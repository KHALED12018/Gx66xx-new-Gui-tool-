#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import pexpect
import shutil
import subprocess

class FirmwareTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dragon-Noir-Gx-Gui")
        self.geometry("800x600")
        self.configure(bg="#1e1e2f")
        self.firmware_path = tk.StringVar()
        self.create_widgets()

    def create_widgets(self):
        container = tk.Frame(self, bg="#2c2c3c", bd=3, relief="raised")
        container.place(relx=0.5, rely=0.5, anchor="center", width=760, height=560)

        tk.Label(container, text="Firmware Path", fg="#ffffff", bg="#2c2c3c", font=("Consolas", 10)).pack(pady=10)
        tk.Entry(container, textvariable=self.firmware_path, width=90, bg="#3c3c4f", fg="#00ffcc", insertbackground="#00ffcc").pack()

        tk.Button(container, text="Upload .bin File", command=self.upload_file, bg="#444466", fg="#ffffff", width=20).pack(pady=10)
        tk.Button(container, text="Unpack", command=self.unpack_firmware, bg="#ff9933", fg="#000000", width=20).pack(pady=5)

        self.output = scrolledtext.ScrolledText(container, height=18, width=90, bg="#1e1e2f", fg="#00ff66", insertbackground="#00ff66", font=("Courier", 10))
        self.output.pack(pady=10)

        tk.Button(container, text="Pack", command=self.pack_firmware, bg="#33cc33", fg="#000000", width=20).pack(pady=5)

    def upload_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Firmware files", "*.bin")])
        if file_path:
            self.firmware_path.set(file_path)

    def unpack_firmware(self):
        bin_file = self.firmware_path.get()
        if not os.path.exists("./.genflash") or not os.access("./.genflash", os.X_OK):
            messagebox.showerror("Error", "genflash not found or not executable.")
            return
        if not os.path.isfile(bin_file):
            messagebox.showerror("Error", "Invalid firmware file.")
            return

        extract_dir = "./extracted"
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)

        try:
            child = pexpect.spawn('./.genflash', encoding='utf-8', timeout=20)
            child.expect(">>")
            child.sendline(f"open {bin_file}")
            child.expect(">>")
            partition_info = child.before

            child.sendline(f"dump {extract_dir}")
            child.expect(">>")
            child.sendline("exit")
            child.close()

            cramfs_path = os.path.join(extract_dir, "ROOT.cramfs")
            root_dir = os.path.join(extract_dir, "ROOT")
            if os.path.isfile(cramfs_path):
                if os.path.isdir(root_dir):
                    shutil.rmtree(root_dir)
                subprocess.run(["unsquashfs", "-d", root_dir, cramfs_path])

            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, partition_info + "\nUnpack completed successfully.\n")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def pack_firmware(self):
        folder = filedialog.askdirectory(title="Select folder with raw partitions")
        if not folder:
            return
        bin_file = self.firmware_path.get()
        if not bin_file or not os.path.isfile(bin_file):
            messagebox.showerror("Error", "Invalid firmware file.")
            return
        try:
            cramfs_image = os.path.join(folder, "ROOT")
            if os.path.isdir(cramfs_image):
                os.system(f"mkcramfs {cramfs_image} {cramfs_image}.cramfs")
                if os.path.isfile(cramfs_image + ".cramfs"):
                    shutil.rmtree(cramfs_image)
                    os.rename(cramfs_image + ".cramfs", cramfs_image)
                elif os.path.isdir(cramfs_image + ".cramfs"):
                    shutil.rmtree(cramfs_image)
                    shutil.move(cramfs_image + ".cramfs", cramfs_image)

            minifs_image = os.path.join(folder, "DATA")
            if os.path.isdir(minifs_image):
                os.system(f"mkminifs {minifs_image} {minifs_image}.minifs")
                if os.path.isfile(minifs_image + ".minifs"):
                    shutil.rmtree(minifs_image)
                    os.rename(minifs_image + ".minifs", minifs_image)
                elif os.path.isdir(minifs_image + ".minifs"):
                    shutil.rmtree(minifs_image)
                    shutil.move(minifs_image + ".minifs", minifs_image)

            child = pexpect.spawn('./.genflash', encoding='utf-8', timeout=30)
            child.expect(">>")
            child.sendline(f"open {bin_file}")
            child.expect(">>")

            for name in sorted(os.listdir(folder)):
                full_path = os.path.join(folder, name)
                if os.path.isfile(full_path):
                    child.sendline(f"add {name} {full_path}")
                    child.expect(">>")

            child.sendline("save f_modified.bin")
            child.expect(">>")
            child.sendline("open f_modified.bin")
            child.expect(">>")
            partition_info = child.before
            child.sendline("exit")
            child.close()

            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, partition_info + "\nPack completed successfully.\n")

        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    app = FirmwareTool()
    app.mainloop()
