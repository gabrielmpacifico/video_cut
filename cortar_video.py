"""Corta um trecho de vídeo sem recodificar (mantém a qualidade original)."""

import shutil
import subprocess
import tempfile
import tkinter as tk
import urllib.request
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox


def parse_time(value: str) -> float:
    """Aceita segundos ou HH:MM:SS[.mmm]."""
    value = value.strip().replace(",", ".")
    try:
        if ":" not in value:
            seconds = float(value)
        else:
            parts = [float(part) for part in value.split(":")]
            if len(parts) == 2:
                seconds = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
            else:
                raise ValueError
        if seconds < 0:
            raise ValueError
        return seconds
    except ValueError:
        raise ValueError("Use segundos (ex.: 75) ou HH:MM:SS (ex.: 00:01:15).")


def choose_input():
    path = filedialog.askopenfilename(
        title="Selecione o vídeo",
        filetypes=[("Vídeos", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.ts"), ("Todos os arquivos", "*.*")],
    )
    if path:
        input_var.set(path)
        output_var.set(str(Path(path).with_name(Path(path).stem + "_cortado" + Path(path).suffix)))


def choose_output():
    path = filedialog.asksaveasfilename(
        title="Salvar trecho como",
        defaultextension=Path(input_var.get()).suffix or ".mp4",
        initialfile=Path(output_var.get()).name if output_var.get() else "trecho_cortado.mp4",
        filetypes=[("Todos os arquivos", "*.*")],
    )
    if path:
        output_var.set(path)


def find_or_download_ffmpeg():
    """Usa uma instalação existente ou baixa o executável portátil para esta pasta."""
    installed = shutil.which("ffmpeg")
    if installed:
        return installed

    local = Path(__file__).resolve().parent / "ffmpeg" / "ffmpeg.exe"
    if local.is_file():
        return str(local)

    status_var.set("Baixando FFmpeg (primeiro uso; requer internet)…")
    root.update_idletasks()
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    target_dir = local.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "ffmpeg.zip"
            request = urllib.request.Request(url, headers={"User-Agent": "VideoCut/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response, archive_path.open("wb") as archive:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    archive.write(block)
            with zipfile.ZipFile(archive_path) as archive:
                exe_name = next(
                    name for name in archive.namelist()
                    if name.lower().endswith("/bin/ffmpeg.exe")
                )
                local.write_bytes(archive.read(exe_name))
        return str(local)
    except Exception:
        local.unlink(missing_ok=True)
        raise


def cut_video():
    source = Path(input_var.get())
    destination = Path(output_var.get())
    if not source.is_file():
        messagebox.showerror("Vídeo não selecionado", "Selecione um arquivo de vídeo existente.")
        return
    if not destination.parent.is_dir():
        messagebox.showerror("Destino inválido", "A pasta de destino não existe.")
        return
    if source.resolve() == destination.resolve():
        messagebox.showerror("Destino inválido", "Escolha um arquivo de saída diferente do original.")
        return
    try:
        start = parse_time(start_var.get())
        end = parse_time(end_var.get())
        if end <= start:
            raise ValueError("O tempo final precisa ser maior que o tempo inicial.")
    except ValueError as error:
        messagebox.showerror("Tempos inválidos", str(error))
        return

    button.configure(state="disabled")
    try:
        ffmpeg = find_or_download_ffmpeg()
        status_var.set("Cortando vídeo…")
        root.update_idletasks()
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(start), "-i", str(source), "-t", str(end - start),
            "-map", "0", "-c", "copy", "-avoid_negative_ts", "make_zero", str(destination),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "O FFmpeg não conseguiu cortar este arquivo.")
        status_var.set("Concluído")
        messagebox.showinfo("Pronto", f"Trecho salvo em:\n{destination}")
    except Exception as error:
        status_var.set("Falha ao cortar")
        messagebox.showerror("Erro ao cortar", f"Não foi possível preparar o FFmpeg ou cortar o vídeo.\n\n{error}")
    finally:
        button.configure(state="normal")


root = tk.Tk()
root.title("Cortar vídeo")
root.resizable(False, False)
root.configure(padx=16, pady=14)
input_var = tk.StringVar()
output_var = tk.StringVar()
start_var = tk.StringVar(value="00:00:00")
end_var = tk.StringVar()
status_var = tk.StringVar(value="")

tk.Label(root, text="Arquivo de vídeo").grid(row=0, column=0, sticky="w", pady=(0, 4))
tk.Entry(root, textvariable=input_var, width=58).grid(row=1, column=0, sticky="ew")
tk.Button(root, text="Procurar…", command=choose_input).grid(row=1, column=1, padx=(8, 0))

tk.Label(root, text="Início (segundos ou HH:MM:SS)").grid(row=2, column=0, sticky="w", pady=(14, 4))
tk.Entry(root, textvariable=start_var, width=24).grid(row=3, column=0, sticky="w")
tk.Label(root, text="Fim (segundos ou HH:MM:SS)").grid(row=4, column=0, sticky="w", pady=(10, 4))
tk.Entry(root, textvariable=end_var, width=24).grid(row=5, column=0, sticky="w")

tk.Label(root, text="Salvar como").grid(row=6, column=0, sticky="w", pady=(14, 4))
tk.Entry(root, textvariable=output_var, width=58).grid(row=7, column=0, sticky="ew")
tk.Button(root, text="Procurar…", command=choose_output).grid(row=7, column=1, padx=(8, 0))

button = tk.Button(root, text="Cortar vídeo", command=cut_video, width=18)
button.grid(row=8, column=0, sticky="w", pady=(16, 4))
tk.Label(root, textvariable=status_var).grid(row=8, column=1, sticky="e")
tk.Label(root, text="O corte é rápido e mantém a qualidade; o ponto pode variar até o próximo keyframe.", fg="#555").grid(
    row=9, column=0, columnspan=2, sticky="w", pady=(8, 0)
)
root.mainloop()
