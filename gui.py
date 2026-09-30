#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeXAS Script Tool GUI
Aplikasi visual khusus engine NeXAS untuk Da Capo III Plus Story (Nintendo Switch)
Mendukung Extract (.binu8 -> .json) dan Insert (.json -> .binu8)
Format JSON:
- Dialog:  {"name": "...", "message": "..."}
- Monolog: {"message": "..."}
"""

import os
import sys
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Import engine logic dari paket src/nexas (implementasi) via wrapper root.
import nexas_tool
import ui_translation_tool
import build_full_patch
import exefs_patch_tool

class NeXASGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NeXAS Script Tool - Da Capo III Plus Story")
        self.geometry("780x640")
        self.minsize(700, 550)

        # Style configuration (Modern Dark Theme)
        self.configure(bg="#1e1e24")
        self.setup_styles()

        # Build UI
        self.create_widgets()

        # Set default paths if available in current directory
        base_dir = Path(os.getcwd())
        script_dir = base_dir / "romfs" / "Script"
        if script_dir.exists():
            self.ext_in_var.set(str(script_dir))
            self.ext_out_var.set(str(base_dir / "romfs" / "Json_New"))
            self.ins_base_var.set(str(script_dir))
            self.ins_json_var.set(str(base_dir / "romfs" / "Json_New"))
            self.ins_out_var.set(str(base_dir / "romfs" / "Script_Mod"))

        # Default UI Translation & Build Patch
        self.ui_out_patch_var.set(str(base_dir / "DC3PS_Indo_Patch"))
        self.bp_out_patch_var.set(str(base_dir / "DC3PS_Indo_Patch"))

        # Prefill CSV terjemahan Indonesia (_id) jika ada
        cfg_id = base_dir / "scratch" / "ui_strings_config_id.csv"
        spm_id = base_dir / "scratch" / "ui_strings_spm_id.csv"
        if cfg_id.exists():
            self.bp_csv_config_var.set(str(cfg_id))
        if spm_id.exists():
            self.bp_csv_spm_var.set(str(spm_id))

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Dark theme colors
        bg_dark = "#1e1e24"
        bg_panel = "#282932"
        accent = "#5c7cfa"
        accent_hover = "#4c6ef5"
        fg_white = "#f8f9fa"
        fg_muted = "#adb5bd"

        style.configure(".", background=bg_dark, foreground=fg_white, font=("Segoe UI", 9))
        style.configure("TNotebook", background=bg_dark, borderwidth=0)
        style.configure("TNotebook.Tab", background=bg_panel, foreground=fg_muted, padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", accent)], foreground=[("selected", "#ffffff")])

        style.configure("TFrame", background=bg_dark)
        style.configure("Panel.TFrame", background=bg_panel, relief="flat")
        style.configure("TLabel", background=bg_panel, foreground=fg_white, font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=bg_panel, foreground="#74c0fc", font=("Segoe UI", 11, "bold"))
        style.configure("Title.TLabel", background=bg_dark, foreground="#ffffff", font=("Segoe UI", 16, "bold"))

        style.configure("Primary.TButton", background=accent, foreground="#ffffff", font=("Segoe UI", 10, "bold"), borderwidth=0, padding=8)
        style.map("Primary.TButton", background=[("active", accent_hover), ("disabled", "#495057")])

        style.configure("Browse.TButton", background="#3b3d4a", foreground="#ffffff", font=("Segoe UI", 9), borderwidth=0, padding=4)
        style.map("Browse.TButton", background=[("active", "#4c4f60")])

    def create_widgets(self):
        # Header banner
        top_frame = tk.Frame(self, bg="#1e1e24", pady=12, padx=20)
        top_frame.pack(fill="x")

        title_lbl = tk.Label(top_frame, text="NeXAS Script Tool", font=("Segoe UI", 16, "bold"), fg="#74c0fc", bg="#1e1e24")
        title_lbl.pack(side="left")
        subtitle_lbl = tk.Label(top_frame, text="Da Capo III Plus Story / Circus / GIGA - Nintendo Switch", font=("Segoe UI", 9), fg="#adb5bd", bg="#1e1e24")
        subtitle_lbl.pack(side="left", padx=12, pady=5)

        # Tab Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="x", padx=20, pady=5)

        # Tab 1: Extract
        self.tab_extract = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_extract, text="  Extract (.binu8 -> .json)  ")
        self.setup_extract_tab()

        # Tab 2: Insert
        self.tab_insert = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_insert, text="  Insert (.json -> .binu8)  ")
        self.setup_insert_tab()

        # Tab 3: UI Translation
        self.tab_ui = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ui, text="  UI Translation  ")
        self.setup_ui_translation_tab()

        # Tab 4: Build Patch Lengkap
        self.tab_build = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_build, text="  Build Patch Lengkap  ")
        self.setup_build_patch_tab()

        # Log frame
        log_frame = tk.Frame(self, bg="#1e1e24", padx=20, pady=10)
        log_frame.pack(fill="both", expand=True)

        log_header = tk.Frame(log_frame, bg="#1e1e24")
        log_header.pack(fill="x", pady=(0, 4))
        tk.Label(log_header, text="Execution Log / Output:", font=("Segoe UI", 9, "bold"), fg="#adb5bd", bg="#1e1e24").pack(side="left")

        clear_btn = tk.Button(log_header, text="Clear Log", command=self.clear_log, bg="#282932", fg="#adb5bd", font=("Segoe UI", 8), relief="flat", padx=6)
        clear_btn.pack(side="right")

        # Text Area with Scrollbar
        text_container = tk.Frame(log_frame, bg="#121316", bd=1, relief="solid")
        text_container.pack(fill="both", expand=True)

        self.log_text = tk.Text(text_container, bg="#14151a", fg="#d1d5db", font=("Consolas", 9), wrap="word", relief="flat", insertbackground="white")
        scrollbar = ttk.Scrollbar(text_container, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        status_bar = tk.Label(self, textvariable=self.status_var, bg="#121316", fg="#adb5bd", font=("Segoe UI", 9), anchor="w", padx=15, pady=4)
        status_bar.pack(fill="x", side="bottom")

    def setup_extract_tab(self):
        panel = ttk.Frame(self.tab_extract, style="Panel.TFrame", padding=15)
        panel.pack(fill="both", expand=True, padx=4, pady=8)

        # Input Row
        ttk.Label(panel, text="Folder Script (.binu8) / File Input:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.ext_in_var = tk.StringVar()
        in_entry = tk.Entry(panel, textvariable=self.ext_in_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid")
        in_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 10))

        btn_box1 = tk.Frame(panel, bg="#282932")
        btn_box1.grid(row=1, column=1, sticky="w", pady=(0, 10))
        ttk.Button(btn_box1, text="Folder...", style="Browse.TButton", command=lambda: self.browse_folder(self.ext_in_var)).pack(side="left", padx=2)
        ttk.Button(btn_box1, text="File...", style="Browse.TButton", command=lambda: self.browse_file(self.ext_in_var, [("NeXAS Script", "*.binu8")])).pack(side="left", padx=2)

        # Output Row
        ttk.Label(panel, text="Folder Output (.json):").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.ext_out_var = tk.StringVar()
        out_entry = tk.Entry(panel, textvariable=self.ext_out_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid")
        out_entry.grid(row=3, column=0, sticky="ew", padx=(0, 6), pady=(0, 10))

        ttk.Button(panel, text="Folder...", style="Browse.TButton", command=lambda: self.browse_folder(self.ext_out_var)).grid(row=3, column=1, sticky="w", pady=(0, 10))

        # Action button
        self.btn_extract = ttk.Button(panel, text="Gas Extract! (.binu8 -> JSON)", style="Primary.TButton", command=self.run_extract)
        self.btn_extract.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        panel.columnconfigure(0, weight=1)

    def setup_insert_tab(self):
        panel = ttk.Frame(self.tab_insert, style="Panel.TFrame", padding=15)
        panel.pack(fill="both", expand=True, padx=4, pady=8)

        # Base binu8
        ttk.Label(panel, text="Folder Asli (.binu8) Base:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.ins_base_var = tk.StringVar()
        base_entry = tk.Entry(panel, textvariable=self.ins_base_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid")
        base_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))

        btn_box2 = tk.Frame(panel, bg="#282932")
        btn_box2.grid(row=1, column=1, sticky="w", pady=(0, 8))
        ttk.Button(btn_box2, text="Folder...", style="Browse.TButton", command=lambda: self.browse_folder(self.ins_base_var)).pack(side="left", padx=2)
        ttk.Button(btn_box2, text="File...", style="Browse.TButton", command=lambda: self.browse_file(self.ins_base_var, [("NeXAS Script", "*.binu8")])).pack(side="left", padx=2)

        # Translated JSON
        ttk.Label(panel, text="Folder JSON Terjemahan (Input):").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.ins_json_var = tk.StringVar()
        json_entry = tk.Entry(panel, textvariable=self.ins_json_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid")
        json_entry.grid(row=3, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))

        btn_box3 = tk.Frame(panel, bg="#282932")
        btn_box3.grid(row=3, column=1, sticky="w", pady=(0, 8))
        ttk.Button(btn_box3, text="Folder...", style="Browse.TButton", command=lambda: self.browse_folder(self.ins_json_var)).pack(side="left", padx=2)
        ttk.Button(btn_box3, text="File...", style="Browse.TButton", command=lambda: self.browse_file(self.ins_json_var, [("JSON Files", "*.json")])).pack(side="left", padx=2)

        # Output Mod binu8
        ttk.Label(panel, text="Folder Output (.binu8 Mod / LayeredFS):").grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.ins_out_var = tk.StringVar()
        out_entry = tk.Entry(panel, textvariable=self.ins_out_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid")
        out_entry.grid(row=5, column=0, sticky="ew", padx=(0, 6), pady=(0, 10))

        ttk.Button(panel, text="Folder...", style="Browse.TButton", command=lambda: self.browse_folder(self.ins_out_var)).grid(row=5, column=1, sticky="w", pady=(0, 10))

        # Word Wrap Row
        wrap_frame = tk.Frame(panel, bg="#282932")
        wrap_frame.grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 14))

        ttk.Label(wrap_frame, text="Panjang WordWrap (0 = Mati / Rekomendasi 56):").pack(side="left", padx=(0, 8))
        self.ins_wrap_var = tk.IntVar(value=56)
        self.wrap_entry = tk.Entry(wrap_frame, textvariable=self.ins_wrap_var, width=8, font=("Segoe UI", 10, "bold"), bg="#14151a", fg="#74c0fc", insertbackground="white", justify="center", bd=1, relief="solid")
        self.wrap_entry.pack(side="left", ipady=2)

        # Quick preset buttons
        tk.Button(wrap_frame, text="56 (Aman / Rekomendasi)", command=lambda: self.ins_wrap_var.set(56), bg="#3b3d4a", fg="#ffffff", font=("Segoe UI", 8), relief="flat", padx=5).pack(side="left", padx=(8, 2))
        tk.Button(wrap_frame, text="52 (Padat)", command=lambda: self.ins_wrap_var.set(52), bg="#3b3d4a", fg="#adb5bd", font=("Segoe UI", 8), relief="flat", padx=5).pack(side="left", padx=2)
        tk.Button(wrap_frame, text="0 (Mati)", command=lambda: self.ins_wrap_var.set(0), bg="#3b3d4a", fg="#adb5bd", font=("Segoe UI", 8), relief="flat", padx=2).pack(side="left", padx=2)

        # Action button
        self.btn_insert = ttk.Button(panel, text="Gas Insert! (JSON -> .binu8)", style="Primary.TButton", command=self.run_insert)
        self.btn_insert.grid(row=7, column=0, columnspan=2, sticky="ew")

        panel.columnconfigure(0, weight=1)

    # ==================================================
    #  Tab 3: UI Translation (ui_translation_tool.py)
    # ==================================================
    def setup_ui_translation_tab(self):
        panel = ttk.Frame(self.tab_ui, style="Panel.TFrame", padding=15)
        panel.pack(fill="both", expand=True, padx=4, pady=8)

        # Baris 0-1: folder patch tujuan
        ttk.Label(panel, text="Folder Patch Tujuan (LayeredFS / DC3PS_Indo_Patch):").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.ui_out_patch_var = tk.StringVar()
        tk.Entry(panel, textvariable=self.ui_out_patch_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        ttk.Button(panel, text="Folder...", style="Browse.TButton", command=lambda: self.browse_folder(self.ui_out_patch_var)).grid(row=1, column=1, sticky="w", pady=(0, 8))

        # Baris 2-3: CSV terjemahan (bisa banyak)
        ttk.Label(panel, text="CSV Terjemahan (ui_strings_config.csv / ui_strings_spm.csv — pilih beberapa):").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.ui_csv_var = tk.StringVar()
        tk.Entry(panel, textvariable=self.ui_csv_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=3, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        btn_box = tk.Frame(panel, bg="#282932")
        btn_box.grid(row=3, column=1, sticky="w", pady=(0, 8))
        ttk.Button(btn_box, text="CSV...", style="Browse.TButton", command=lambda: self.browse_files(self.ui_csv_var, [("CSV Files", "*.csv")])).pack(side="left", padx=2)

        # Baris 4-5: folder PNG hasil edit (untuk pack-png)
        ttk.Label(panel, text="Folder PNG Hasil Edit (kosong = png_work/edited):", ).grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.ui_png_var = tk.StringVar(value=str(Path(os.getcwd()) / "png_work" / "edited"))
        tk.Entry(panel, textvariable=self.ui_png_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=5, column=0, sticky="ew", padx=(0, 6), pady=(0, 10))
        ttk.Button(panel, text="Folder...", style="Browse.TButton", command=lambda: self.browse_folder(self.ui_png_var)).grid(row=5, column=1, sticky="w", pady=(0, 10))

        # Tombol aksi (6 mode + ExeFS)
        actions = tk.Frame(panel, bg="#282932")
        actions.grid(row=6, column=0, columnspan=2, sticky="ew")
        actions.columnconfigure((0, 1, 2), weight=1)

        self.ui_buttons = {}
        def add_btn(text, col, cmd, primary=True):
            b = ttk.Button(actions, text=text, style="Primary.TButton" if primary else "Browse.TButton", command=cmd)
            b.grid(row=0 if primary else 1, column=col, sticky="ew", padx=3, pady=3)
            self.ui_buttons[text.split(" ")[0]] = b

        add_btn("Extract UI (SPM+Config -> CSV)", 0, self.run_ui_extract)
        add_btn("Audit PNG (kandidat teks JP)", 1, self.run_ui_audit)
        add_btn("Export PNG (ke png_work/src)", 2, self.run_ui_export)
        add_btn("Apply Config (CSV -> .datu8)", 0, self.run_ui_apply_config)
        add_btn("Apply SPM (CSV -> .spm)", 1, self.run_ui_apply_spm)
        add_btn("Pack PNG (edited -> patch)", 2, self.run_ui_pack_png, primary=False)
        add_btn("Scan ExeFS (pesan info)", 0, self.run_ui_scan_exefs, primary=False)
        add_btn("ExeFS Apply (CSV -> main)", 1, self.run_ui_apply_exefs, primary=False)
        add_btn("Discover ExeFS (isi CSV otomatis)", 2, self.run_ui_discover_exefs, primary=False)

        hint = ttk.Label(panel, text=(
            "Alur kerja: Extract UI -> isi kolom 'indonesian_translation' di CSV -> Apply Config / Apply SPM.\n"
            "Untuk label bergambar: Audit PNG -> Export PNG -> edit di Photoshop/GIMP (simpan ke png_work/edited) -> Pack PNG.\n"
            "Apply Config/SPM otomatis menulis .datu8/.spm ke folder patch tujuan; PNG dikonversi formatnya otomatis."))
        hint.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 0))
        hint.configure(foreground="#adb5bd", font=("Segoe UI", 8))

        panel.columnconfigure(0, weight=1)

    def run_ui_scan_exefs(self):
        def task():
            self.log("[*] Scan ExeFS: mencari string pesan info di scratch/exefs_dump/main ...")
            rc = exefs_patch_tool.cmd_scan()
            if rc == 0:
                self.log("[+] Scan selesai. Edit scratch/exefs_messages.csv bila ingin revisi.")
        self.ui_thread(self.ui_buttons["Scan"], "Scan ExeFS...", task)

    def run_ui_apply_exefs(self):
        def task():
            self.log("[*] ExeFS Apply: menerapkan CSV pesan info ke dump main ...")
            res = exefs_patch_tool.patch_dump(
                str(Path(os.getcwd()) / "scratch" / "exefs_dump"),
                str(Path(os.getcwd()) / "scratch" / "exefs_messages.csv"),
                str(Path(os.getcwd()) / "scratch" / "exefs_patch"))
            if res["ok"]:
                eden_main = Path(os.environ.get("APPDATA", "")) / "eden" / "exefs" / "010041601B544000" / "main"
                if Path(os.environ.get("APPDATA", "")).joinpath("eden").exists():
                    import shutil
                    eden_main.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(res["out"], eden_main)
                    self.log("[+] Terpasang ke Eden: %s" % eden_main)
                    messagebox.showinfo("Sukses", "ExeFS patch terpasang ke Eden!\n%s\n\n%d penggantian." % (eden_main, res["total"]))
                else:
                    messagebox.showinfo("Sukses", "Patch dibuat: %s\n(salin manual ke folder exefs emulator)" % res["out"])
            else:
                messagebox.showwarning("Tidak dipatch", res["reason"] or "Tidak ada yang diganti.")
        self.ui_thread(self.ui_buttons["ExeFS"], "ExeFS Apply...", task)

    def run_ui_discover_exefs(self):
        def task():
            self.log("[*] Discover ExeFS: memindai dump main untuk string pesan Jepang ...")
            csv_path = str(Path(os.getcwd()) / "scratch" / "exefs_messages.csv")
            dump_dir = str(Path(os.getcwd()) / "scratch" / "exefs_dump")
            n = exefs_patch_tool.discover_to_csv(dump_dir, csv_path)
            exefs_patch_tool.write_guide(str(Path(os.getcwd()) / "scratch"))
            if n:
                self.log("[+] %d baris BARU di %s" % (n, csv_path))
                self.log("    PANDUAN wajib baca: scratch/exefs_messages_BACA_SAYA.txt")
                messagebox.showinfo("Discover selesai", "%d string baru ditambahkan ke CSV\n\nWAJIB baca panduan isi:\nscratch\\exefs_messages_BACA_SAYA.txt\n\nTerjemahan kosong = aman (tidak diganti).\nIsi lalu klik ExeFS Apply." % n)
            else:
                messagebox.showinfo("Discover selesai", "Tidak ada string baru (CSV sudah lengkap / dump tidak ada).")
        self.ui_thread(self.ui_buttons["Discover"], "Discover ExeFS...", task)

    def ui_thread(self, btn, status, task):
        btn.config(state="disabled")
        self.status_var.set(status)

        def wrap():
            try:
                task()
                self.status_var.set("Selesai!")
            except Exception as e:
                self.log(f"[!] Error: {e}")
                self.log(traceback.format_exc())
                self.status_var.set("Error.")
                messagebox.showerror("Error", str(e))
            finally:
                btn.config(state="normal")

        threading.Thread(target=wrap, daemon=True).start()

    def run_ui_extract(self):
        def task():
            self.log("[*] Extract UI: memindai System/*.spm + Config/*.datu8 ...")
            ui_translation_tool.extract_all(str(Path(os.getcwd()) / "scratch"))
            self.log("[+] Selesai! CSV tersimpan di folder scratch/ — isi kolom indonesian_translation.")
            messagebox.showinfo("Sukses", "Extract UI selesai! CSV ada di folder scratch/.")
        self.ui_thread(self.ui_buttons["Extract"], "Extract UI...", task)

    def run_ui_audit(self):
        def task():
            self.log("[*] Audit PNG: memindai romfs/System/*.png (heuristik nama file) ...")
            ui_translation_tool.audit_png(str(Path(os.getcwd()) / "scratch"))
            self.log("[+] Selesai! Buka scratch/png_text_audit.html untuk review visual.")
            messagebox.showinfo("Sukses", "Audit PNG selesai! Lihat scratch/png_text_audit.html")
        self.ui_thread(self.ui_buttons["Audit"], "Audit PNG...", task)

    def run_ui_export(self):
        def task():
            self.log("[*] Export PNG kandidat ke png_work/src/ ...")
            ui_translation_tool.export_png(str(Path(os.getcwd()) / "png_work"))
            messagebox.showinfo("Sukses", "PNG diekspor ke png_work/src/. Edit lalu jalankan Pack PNG.")
        self.ui_thread(self.ui_buttons["Export"], "Export PNG...", task)

    def run_ui_apply_config(self):
        csvs = [p.strip() for p in self.ui_csv_var.get().split(";") if p.strip() and p.strip().lower().endswith(".csv")]
        if not csvs:
            messagebox.showerror("Error", "Pilih file CSV terjemahan dulu (mis. scratch/ui_strings_config.csv)!")
            return
        def task():
            self.log("[*] Apply Config: menerapkan CSV -> .datu8 ke folder patch ...")
            ui_translation_tool.apply_config_csv(csvs, self.ui_out_patch_var.get().strip())
            messagebox.showinfo("Sukses", "Config .datu8 diterapkan ke folder patch!")
        self.ui_thread(self.ui_buttons["Apply"], "Apply Config...", task)

    def run_ui_apply_spm(self):
        csvs = [p.strip() for p in self.ui_csv_var.get().split(";") if p.strip() and p.strip().lower().endswith(".csv")]
        if not csvs:
            messagebox.showerror("Error", "Pilih file CSV terjemahan dulu (mis. scratch/ui_strings_spm.csv)!")
            return
        def task():
            for c in csvs:
                self.log(f"[*] Apply SPM: {c} -> .spm ke folder patch ...")
                ui_translation_tool.apply_spm_csv(c, self.ui_out_patch_var.get().strip())
            messagebox.showinfo("Sukses", "SPM diterapkan ke folder patch!")
        self.ui_thread(self.ui_buttons["Apply"], "Apply SPM...", task)

    def run_ui_pack_png(self):
        edited = self.ui_png_var.get().strip()
        if not edited or not os.path.isdir(edited):
            messagebox.showerror("Error", "Folder PNG hasil edit tidak ditemukan!")
            return
        def task():
            self.log("[*] Pack PNG: validasi + konversi format otomatis ...")
            res = ui_translation_tool.pack_png_to_patch(edited, self.ui_out_patch_var.get().strip())
            if res["packed"]:
                messagebox.showinfo("Sukses", f"{res['packed']} PNG dikemas ({res['converted']} dikonversi otomatis)!")
            else:
                messagebox.showwarning("Tidak ada", "Tidak ada PNG yang dikemas. Cek log.")
        self.ui_thread(self.ui_buttons["Pack"], "Pack PNG...", task)

    # ==================================================
    #  Tab 4: Build Patch Lengkap (build_full_patch.py)
    # ==================================================
    def setup_build_patch_tab(self):
        panel = ttk.Frame(self.tab_build, style="Panel.TFrame", padding=15)
        panel.pack(fill="both", expand=True, padx=4, pady=8)

        ttk.Label(panel, text="Folder Patch Output:").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.bp_out_patch_var = tk.StringVar()
        tk.Entry(panel, textvariable=self.bp_out_patch_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        ttk.Button(panel, text="Folder...", style="Browse.TButton", command=lambda: self.browse_folder(self.bp_out_patch_var)).grid(row=1, column=1, sticky="w", pady=(0, 8))

        # Pilihan komponen
        ttk.Label(panel, text="Komponen yang dibangun:").grid(row=2, column=0, sticky="w", pady=(0, 4))
        comp_frame = tk.Frame(panel, bg="#282932")
        comp_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 10))
        self.bp_vars = {}
        for i, key in enumerate(build_full_patch.COMPONENTS):
            var = tk.BooleanVar(value=True)
            self.bp_vars[key] = var
            label = {
                "script": "Naskah Scenario (.binu8)",
                "ui-config": "UI Config (.datu8)",
                "ui-spm": "UI Layout (.spm)",
                "ui-png": "UI Tekstur (PNG)",
                "video": "Video Lirik OP (Movie/dc3ps_op.mp4)",
                "exefs": "Pesan Info ExeFS (dump milikmu)",
            }.get(key, key)
            # grid 3 kolom x N baris supaya semua checkbox terlihat (tidak terpotong)
            tk.Checkbutton(comp_frame, text=label, variable=var, bg="#282932", fg="#f8f9fa", selectcolor="#1e1e24", activebackground="#282932", activeforeground="#ffffff").grid(row=i // 3, column=i % 3, sticky="w", padx=8, pady=2)

        # CSV terjemahan (config & spm) untuk komponen UI
        ttk.Label(panel, text="CSV Config terjemahan (bisa beberapa; kosong = default scratch):", ).grid(row=4, column=0, sticky="w", pady=(0, 4))
        self.bp_csv_config_var = tk.StringVar()
        tk.Entry(panel, textvariable=self.bp_csv_config_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=5, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        ttk.Button(panel, text="CSV...", style="Browse.TButton", command=lambda: self.browse_files(self.bp_csv_config_var, [("CSV Files", "*.csv")])).grid(row=5, column=1, sticky="w", pady=(0, 8))

        ttk.Label(panel, text="CSV SPM terjemahan (kosong = default scratch):", ).grid(row=6, column=0, sticky="w", pady=(0, 4))
        self.bp_csv_spm_var = tk.StringVar()
        tk.Entry(panel, textvariable=self.bp_csv_spm_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=7, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        ttk.Button(panel, text="CSV...", style="Browse.TButton", command=lambda: self.browse_file(self.bp_csv_spm_var, [("CSV Files", "*.csv")])).grid(row=7, column=1, sticky="w", pady=(0, 8))

        # Video opsional
        ttk.Label(panel, text="Video Lirik OP (kosong = auto-detect Movie/dc3ps_op.mp4):", ).grid(row=8, column=0, sticky="w", pady=(0, 4))
        self.bp_video_var = tk.StringVar()
        tk.Entry(panel, textvariable=self.bp_video_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=9, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        ttk.Button(panel, text="File...", style="Browse.TButton", command=lambda: self.browse_file(self.bp_video_var, [("MP4 Video", "*.mp4")])).grid(row=9, column=1, sticky="w", pady=(0, 8))

        # ExeFS: file main (dump) + CSV pesan info
        ttk.Label(panel, text="ExeFS: file main hasil dump (kosong = scratch/exefs_dump/main):", ).grid(row=10, column=0, sticky="w", pady=(0, 4))
        self.bp_exefs_main_var = tk.StringVar()
        tk.Entry(panel, textvariable=self.bp_exefs_main_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=11, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        ttk.Button(panel, text="File...", style="Browse.TButton", command=lambda: self.browse_file(self.bp_exefs_main_var, [("NSO main", "*"), ("Semua file", "*.*")])).grid(row=11, column=1, sticky="w", pady=(0, 8))

        ttk.Label(panel, text="ExeFS: CSV pesan info (kosong = scratch/exefs_messages.csv):", ).grid(row=12, column=0, sticky="w", pady=(0, 4))
        self.bp_exefs_csv_var = tk.StringVar()
        tk.Entry(panel, textvariable=self.bp_exefs_csv_var, font=("Segoe UI", 9), bg="#1e1e24", fg="#ffffff", insertbackground="white", bd=1, relief="solid").grid(row=13, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        ttk.Button(panel, text="CSV...", style="Browse.TButton", command=lambda: self.browse_file(self.bp_exefs_csv_var, [("CSV Files", "*.csv")])).grid(row=13, column=1, sticky="w", pady=(0, 8))

        # Opsi pasca-build
        opt_frame = tk.Frame(panel, bg="#282932")
        opt_frame.grid(row=14, column=0, columnspan=2, sticky="w", pady=(0, 10))
        self.bp_zip_var = tk.BooleanVar(value=False)
        self.bp_install_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opt_frame, text="Buat paket ZIP rilis (Atmosphere/Emulator/Ryujinx)", variable=self.bp_zip_var, bg="#282932", fg="#f8f9fa", selectcolor="#1e1e24", activebackground="#282932", activeforeground="#ffffff").pack(anchor="w")
        tk.Checkbutton(opt_frame, text="Pasang otomatis ke emulator Eden setelah build", variable=self.bp_install_var, bg="#282932", fg="#f8f9fa", selectcolor="#1e1e24", activebackground="#282932", activeforeground="#ffffff").pack(anchor="w")

        self.btn_build = ttk.Button(panel, text="Gas Build Patch Lengkap!", style="Primary.TButton", command=self.run_build_patch)
        self.btn_build.grid(row=15, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        hint = ttk.Label(panel, text=(
            "Menggabungkan SEMUA terjemahan ke satu patch: scenario (.binu8 dari tab Insert), UI datu8/SPM\n"
            "(CSV di atas), PNG hasil edit, video lirik OP, dan pesan info ExeFS (file main + CSV ExeFS di atas)\n"
            "— komponen yang sumbernya kosong dilewati. Hasil ExeFS TIDAK ikut ZIP distribusi\n"
            "(kode berhak cipta), hanya dipasang ke emulator lokal."))
        hint.grid(row=16, column=0, columnspan=2, sticky="w", pady=(10, 0))
        hint.configure(foreground="#adb5bd", font=("Segoe UI", 8))

        panel.columnconfigure(0, weight=1)

    def run_build_patch(self):
        out_patch = self.bp_out_patch_var.get().strip()
        if not out_patch:
            messagebox.showerror("Error", "Tentukan folder patch output!")
            return
        only = [k for k, v in self.bp_vars.items() if v.get()]
        if not only:
            messagebox.showerror("Error", "Pilih minimal satu komponen!")
            return

        class Args: pass
        args = Args()
        args.out_patch = out_patch
        args.only = ",".join(only)
        args.script_dir = str(Path(os.getcwd()) / "romfs" / "Script_Mod")
        cfg_csvs = [p.strip() for p in self.bp_csv_config_var.get().split(";") if p.strip()]
        if not cfg_csvs:
            cfg_csvs = [str(Path(os.getcwd()) / "scratch" / "ui_strings_config.csv")]
        args.csv_config = cfg_csvs
        args.csv_spm = self.bp_csv_spm_var.get().strip() or str(Path(os.getcwd()) / "scratch" / "ui_strings_spm.csv")
        args.png_edited = str(Path(os.getcwd()) / "png_work" / "edited")
        args.video = self.bp_video_var.get().strip() or None
        args.zip = self.bp_zip_var.get()
        args.install = self.bp_install_var.get()
        # ExeFS: file main pilihan user dipakai untuk patch.
        # PENTING: JANGAN menimpa dump asli scratch/exefs_dump/main — dulu ini
        # merusak dump (tertimpa hasil patch). Pakai patch_dump() langsung pada
        # file pilihan user, tanpa menyentuh folder dump.
        main_sel = self.bp_exefs_main_var.get().strip()
        dump_dir = Path(os.getcwd()) / "scratch" / "exefs_dump"
        args.exefs_dump = main_sel if (main_sel and os.path.isfile(main_sel)) else str(dump_dir)
        args.exefs_csv = self.bp_exefs_csv_var.get().strip() or str(Path(os.getcwd()) / "scratch" / "exefs_messages.csv")
        args.exefs_out = str(Path(os.getcwd()) / "scratch" / "exefs_patch")

        self.btn_build.config(state="disabled")
        self.status_var.set("Membangun patch lengkap...")

        def task():
            try:
                # Redirect print() dari builder ke log GUI
                import builtins
                orig_print = builtins.print
                def log_print(*a, **kw):
                    msg = " ".join(str(x) for x in a)
                    self.log(msg)
                builtins.print = log_print
                try:
                    rc = build_full_patch.build(args)
                finally:
                    builtins.print = orig_print
                if rc == 0:
                    self.status_var.set("Build patch selesai!")
                    messagebox.showinfo("Sukses", f"Patch lengkap selesai dibangun di:\n{out_patch}")
                else:
                    self.status_var.set("Build gagal.")
            except Exception as e:
                self.log(f"[!] Error: {e}")
                self.log(traceback.format_exc())
                self.status_var.set("Error saat build.")
                messagebox.showerror("Error", str(e))
            finally:
                self.btn_build.config(state="normal")

        threading.Thread(target=task, daemon=True).start()

    def browse_folder(self, target_var):
        path = filedialog.askdirectory()
        if path:
            target_var.set(os.path.normpath(path))

    def browse_files(self, target_var, filetypes):
        paths = filedialog.askopenfilenames(filetypes=filetypes)
        if paths:
            target_var.set(";".join(os.path.normpath(p) for p in paths))

    def browse_file(self, target_var, filetypes):
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            target_var.set(os.path.normpath(path))

    def log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    def clear_log(self):
        self.log_text.delete("1.0", "end")

    def run_extract(self):
        in_path = self.ext_in_var.get().strip()
        out_path = self.ext_out_var.get().strip()

        if not in_path or not os.path.exists(in_path):
            messagebox.showerror("Error", "Path input script (.binu8) tidak valid atau tidak ditemukan!")
            return
        if not out_path:
            messagebox.showerror("Error", "Tentukan path output JSON!")
            return

        self.btn_extract.config(state="disabled")
        self.status_var.set("Extracting script...")

        def task():
            try:
                p_in = Path(in_path)
                p_out = Path(out_path)

                if p_in.is_file():
                    self.log(f"[*] Extracting single file: {p_in.name}...")
                    if p_out.suffix.lower() != '.json':
                        p_out = p_out / (p_in.stem + '.json')
                    cnt = nexas_tool.extract_script(str(p_in), str(p_out))
                    self.log(f"[+] Selesai! Berhasil mengekstrak {cnt} baris ke: {p_out.name}")
                else:
                    files = [f for f in p_in.glob('**/*.binu8') if f.name != '__global.binu8']
                    self.log(f"[*] Menemukan {len(files)} file .binu8 di {p_in}...")
                    total_cnt = 0
                    for f in sorted(files):
                        rel = f.relative_to(p_in)
                        dst = p_out / rel.with_suffix('.json')
                        cnt = nexas_tool.extract_script(str(f), str(dst))
                        total_cnt += cnt
                        self.log(f"  - {f.name}: {cnt} dialog/monolog diekstrak")
                    self.log(f"[+] SELESAI! Total {len(files)} file ({total_cnt} dialog/monolog) tersimpan di:\n    {p_out}")

                self.status_var.set("Extract selesai!")
                messagebox.showinfo("Sukses", "Ekstraksi script selesai dengan sukses!")
            except Exception as e:
                self.log(f"[!] Error saat ekstraksi: {e}")
                self.status_var.set("Error saat ekstraksi.")
                messagebox.showerror("Error", f"Terjadi kesalahan: {e}")
            finally:
                self.btn_extract.config(state="normal")

        threading.Thread(target=task, daemon=True).start()

    def run_insert(self):
        base_path = self.ins_base_var.get().strip()
        json_path = self.ins_json_var.get().strip()
        out_path = self.ins_out_var.get().strip()
        wrap_val = self.ins_wrap_var.get()

        if not base_path or not os.path.exists(base_path):
            messagebox.showerror("Error", "Path base (.binu8 asli) tidak ditemukan!")
            return
        if not json_path or not os.path.exists(json_path):
            messagebox.showerror("Error", "Path JSON terjemahan tidak ditemukan!")
            return
        if not out_path:
            messagebox.showerror("Error", "Tentukan path folder output mod!")
            return

        self.btn_insert.config(state="disabled")
        self.status_var.set("Inserting translated script...")

        def task():
            try:
                b_p = Path(base_path)
                j_p = Path(json_path)
                o_p = Path(out_path)

                if b_p.is_file() and j_p.is_file():
                    self.log(f"[*] Rebuilding single file: {b_p.name} (WordWrap={wrap_val})...")
                    if o_p.suffix.lower() != '.binu8':
                        o_p = o_p / b_p.name
                    cnt = nexas_tool.insert_script(str(b_p), str(j_p), str(o_p), word_wrap=wrap_val)
                    self.log(f"[+] Selesai! {cnt} baris terjemahan berhasil diinjeksi ke: {o_p.name}")
                else:
                    json_files = list(j_p.glob('**/*.json'))
                    self.log(f"[*] Menemukan {len(json_files)} file JSON di {j_p} (WordWrap={wrap_val})...")
                    inserted_cnt = 0
                    for jf in sorted(json_files):
                        rel = jf.relative_to(j_p)
                        bin_orig = b_p / rel.with_suffix('.binu8')
                        if not bin_orig.exists():
                            self.log(f"  [Skip] Base binu8 tidak ditemukan untuk: {jf.name}")
                            continue
                        bin_out = o_p / rel.with_suffix('.binu8')
                        cnt = nexas_tool.insert_script(str(bin_orig), str(jf), str(bin_out), word_wrap=wrap_val)
                        inserted_cnt += 1
                        self.log(f"  - Injected {jf.name} -> {bin_out.name} ({cnt} baris)")
                    self.log(f"[+] SELESAI! Berhasil merekonstruksi {inserted_cnt} file .binu8 ke:\n    {o_p}")

                # Copy custom system.datu8 to mod Config if available
                custom_cfg = Path(os.getcwd()) / "romfs" / "Custom Config" / "system.datu8"
                if custom_cfg.exists():
                    target_cfg_dir = o_p.parent / "Config"
                    target_cfg_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    shutil.copy2(str(custom_cfg), str(target_cfg_dir / "system.datu8"))
                    self.log(f"[+] Otomatis menyertakan file font Custom Config:\n    -> {target_cfg_dir / 'system.datu8'}")

                self.status_var.set("Insert selesai!")
                messagebox.showinfo("Sukses", "Injeksi script selesai dengan sukses!")
            except Exception as e:
                self.log(f"[!] Error saat insert: {e}")
                self.status_var.set("Error saat insert.")
                messagebox.showerror("Error", f"Terjadi kesalahan: {e}")
            finally:
                self.btn_insert.config(state="normal")

        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    app = NeXASGUI()
    app.mainloop()
