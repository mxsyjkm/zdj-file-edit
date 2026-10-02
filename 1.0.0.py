import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
from datetime import datetime

ENCODING = "utf-8-sig"

# ==================== ZDJ 核心编解码 ====================

DIGIT0 = "哦"   # 三进制 0
DIGIT1 = "噢"   # 三进制 1
DIGIT2 = "鼩"   # 三进制 2

DIGIT_MAP = {0: DIGIT0, 1: DIGIT1, 2: DIGIT2}
REVERSE_MAP = {DIGIT0: 0, DIGIT1: 1, DIGIT2: 2}

VALID_CHARS = set(DIGIT_MAP.values())


def encode_char(ch):
    """任意字符 -> 三进制符号串"""
    n = ord(ch)
    if n == 0:
        return DIGIT0
    digits = []
    while n > 0:
        digits.append(n % 3)
        n //= 3
    digits.reverse()
    return "".join(DIGIT_MAP[d] for d in digits)


def encode_text(text):
    """整段文本编码，字符之间用空格分隔"""
    return " ".join(encode_char(ch) for ch in text)


def decode_token(tok):
    """三进制符号串 -> 字符"""
    n = 0
    for ch in tok:
        if ch not in REVERSE_MAP:
            return "?"
        n = n * 3 + REVERSE_MAP[ch]
    try:
        return chr(n)
    except ValueError:
        return "?"


def decode_text(encoded):
    """整段解码，按空格分割"""
    result = []
    for tok in encoded.split(" "):
        if tok:
            result.append(decode_token(tok))
    return "".join(result)


def contains_plain_letters(encoded: str) -> bool:
    """检查编码文本里是否混入了非鼩噢哦字符（防原文泄漏）"""
    for ch in encoded:
        if ch in " \t\r\n":
            continue
        if ch not in VALID_CHARS:
            return True
    return False


# ==================== 界面 ====================

class ZDJEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("ZDJ编辑器 v1.0")
        self.root.geometry("500x700")
        self.root.resizable(True, True)

        self.version = "v1.0"
        self.config_file = "zdj_config.json"
        self.default_storage = os.path.join(os.path.expanduser("~"), "ZDJ_Files")
        if not os.path.exists(self.default_storage):
            os.makedirs(self.default_storage)

        self.current_folder = self.load_config()
        self.current_file = None
        self.setup_ui()

    # ---------- 配置 ----------

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding=ENCODING) as f:
                    return json.load(f).get('storage_path', self.default_storage)
            except:
                pass
        return self.default_storage

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding=ENCODING) as f:
                json.dump({'storage_path': self.current_folder}, f, ensure_ascii=False)
        except:
            pass

    # ---------- UI ----------

    def setup_ui(self):
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="ZDJ编辑器 v1.0", font=("Arial", 12, "bold")).pack(pady=6)

        folder_frame = ttk.LabelFrame(main, text="存储位置", padding="6")
        folder_frame.pack(fill=tk.X, pady=4)

        self.folder_var = tk.StringVar(value=self.current_folder)
        ttk.Label(folder_frame, textvariable=self.folder_var, wraplength=460).pack(fill=tk.X)

        fb = ttk.Frame(folder_frame)
        fb.pack(fill=tk.X, pady=3)
        ttk.Button(fb, text="更改位置", command=self.select_folder).pack(side=tk.LEFT)
        ttk.Button(fb, text="打开文件夹", command=self.open_folder).pack(side=tk.LEFT, padx=6)

        list_frame = ttk.LabelFrame(main, text="ZDJ文件", padding="6")
        list_frame.pack(fill=tk.X, pady=4)

        lb = ttk.Frame(list_frame)
        lb.pack(fill=tk.X)
        ttk.Button(lb, text="刷新", command=self.refresh_file_list).pack(side=tk.LEFT)
        ttk.Button(lb, text="查看", command=self.view_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(lb, text="编辑", command=self.edit_selected).pack(side=tk.LEFT, padx=6)
        ttk.Button(lb, text="删除", command=self.delete_selected).pack(side=tk.LEFT, padx=6)

        self.file_listbox = tk.Listbox(list_frame, height=5, font=("Arial", 9))
        self.file_listbox.pack(fill=tk.BOTH, expand=True, pady=4)
        self.file_listbox.bind('<Double-Button-1>', lambda e: self.view_selected())

        edit_frame = ttk.LabelFrame(main, text="编辑内容", padding="6")
        edit_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        ttk.Label(edit_frame, text="文件名:").pack(anchor=tk.W)
        self.filename_var = tk.StringVar()
        ttk.Entry(edit_frame, textvariable=self.filename_var).pack(fill=tk.X, pady=3)

        ttk.Label(edit_frame, text="原文:").pack(anchor=tk.W, pady=(6, 0))
        self.plain_text = scrolledtext.ScrolledText(
            edit_frame, height=12, wrap=tk.WORD, font=("Arial", 11)
        )
        self.plain_text.pack(fill=tk.BOTH, expand=True, pady=3)

        btn_frame = ttk.Frame(edit_frame)
        btn_frame.pack(fill=tk.X, pady=6)
        ttk.Button(btn_frame, text="清空", command=self.clear_all).pack(side=tk.LEFT, padx=3)

        action = ttk.Frame(main)
        action.pack(fill=tk.X, pady=6)
        ttk.Button(action, text="新建ZDJ文件", command=self.create_file).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(action, text="保存修改", command=self.save_file).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main, textvariable=self.status_var, relief=tk.SUNKEN).pack(
            fill=tk.X, pady=(6, 0))

        self.refresh_file_list()

    # ---------- 基础操作 ----------

    def update_status(self, msg):
        self.status_var.set(msg)
        print("状态:", msg)

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_folder)
        if folder:
            self.current_folder = folder
            self.folder_var.set(folder)
            self.save_config()
            self.refresh_file_list()

    def open_folder(self):
        try:
            os.startfile(self.current_folder)
        except Exception as e:
            self.update_status(f"打开失败: {e}")

    def refresh_file_list(self):
        self.file_listbox.delete(0, tk.END)
        try:
            files = [f for f in os.listdir(self.current_folder) if f.endswith('.zdj')]
            for f in sorted(files):
                self.file_listbox.insert(tk.END, f)
            self.update_status(f"共 {len(files)} 个文件")
        except Exception as e:
            self.update_status(f"刷新失败: {e}")

    def clear_all(self):
        self.plain_text.delete("1.0", tk.END)
        self.filename_var.set("")
        self.current_file = None
        self.update_status("已清空")

    # ---------- 文件读写（只写编码，绝不写原文） ----------

    def _write_zdj(self, path, encoded, created=""):
        if contains_plain_letters(encoded):
            raise ValueError(
                "检测到文件内容中混入了非编码字符（原文），已拒绝保存！\n"
                "ZDJ 文件只允许保存鼩/噢/哦 和空格。"
            )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(path, 'w', encoding=ENCODING, newline='\n') as f:
            f.write("#ZDJ\n")
            f.write(f"#{self.version}\n")
            f.write("#Type: text\n")
            f.write(f"#Created: {created if created else now}\n")
            f.write(f"#Modified: {now}\n")
            f.write(encoded + "\n")

    def _read_zdj(self, path):
        for enc in (ENCODING, "utf-8", "gbk"):
            try:
                with open(path, 'r', encoding=enc) as f:
                    return f.read().splitlines()
            except (UnicodeDecodeError, LookupError):
                continue
        with open(path, 'r', encoding="utf-8", errors="ignore") as f:
            return f.read().splitlines()

    # ---------- 文件操作 ----------

    def create_file(self):
        name = self.filename_var.get().strip()
        if not name:
            messagebox.showerror("错误", "请输入文件名")
            return
        if not name.endswith('.zdj'):
            name += '.zdj'

        text = self.plain_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("错误", "请输入原文")
            return

        encoded = encode_text(text)
        path = os.path.join(self.current_folder, name)
        try:
            self._write_zdj(path, encoded)
            self.update_status(f"创建成功: {name}")
            self.refresh_file_list()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def save_file(self):
        if not self.current_file:
            messagebox.showwarning("提示", "请先选择要修改的文件")
            return

        text = self.plain_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("错误", "原文为空")
            return

        encoded = encode_text(text)
        try:
            created = ""
            if os.path.exists(self.current_file):
                for line in self._read_zdj(self.current_file):
                    if line.startswith("#Created:"):
                        created = line.split(":", 1)[1].strip()
                        break
            self._write_zdj(self.current_file, encoded, created)
            self.update_status(f"保存成功: {os.path.basename(self.current_file)}")
            self.refresh_file_list()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def view_selected(self):
        sel = self.file_listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择文件")
            return
        name = self.file_listbox.get(sel[0])
        path = os.path.join(self.current_folder, name)

        try:
            version = "未知版本"
            created_time = "未知时间"
            modified_time = "无记录"
            file_type = "text"
            encoded = ""

            for line in self._read_zdj(path):
                if not line:
                    continue
                if line.startswith("#ZDJ"):
                    continue
                elif line.startswith("#v"):
                    version = line[1:].strip()
                elif line.startswith("#Type:"):
                    file_type = line.split(":", 1)[1].strip()
                elif line.startswith("#Created:"):
                    created_time = line.split(":", 1)[1].strip()
                elif line.startswith("#Modified:"):
                    modified_time = line.split(":", 1)[1].strip()
                elif line and not line.startswith("#"):
                    encoded += line.strip()

            decoded = decode_text(encoded)

            self.root.update_idletasks()
            root_x = self.root.winfo_x()
            root_y = self.root.winfo_y()
            root_w = self.root.winfo_width()
            root_h = self.root.winfo_height()

            win_w = max(500, root_w - 40)
            win_h = max(600, root_h - 40)
            win_x = root_x + 20
            win_y = root_y + 20

            win = tk.Toplevel(self.root)
            win.title(f"查看: {name}")
            win.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
            win.resizable(True, True)

            info_frame = ttk.LabelFrame(win, text="文件信息", padding="8")
            info_frame.pack(fill=tk.X, padx=8, pady=8)

            ttk.Label(info_frame, text=f"文件: {name}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"类型: {file_type}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"版本: {version}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"创建: {created_time}").pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"修改: {modified_time}").pack(anchor=tk.W)
            ttk.Label(info_frame, text="加密状态: 未加密", foreground="gray").pack(anchor=tk.W)

            content_frame = ttk.LabelFrame(win, text="内容预览", padding="8")
            content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

            text_widget = scrolledtext.ScrolledText(
                content_frame, wrap=tk.WORD, font=("Arial", 11)
            )
            text_widget.pack(fill=tk.BOTH, expand=True)

            text_widget.insert(tk.END, decoded)
            text_widget.config(state=tk.DISABLED)

            ttk.Button(win, text="关闭", command=win.destroy).pack(pady=8)

        except Exception as e:
            messagebox.showerror("错误", f"查看失败: {e}")

    def edit_selected(self):
        sel = self.file_listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择文件")
            return
        name = self.file_listbox.get(sel[0])
        path = os.path.join(self.current_folder, name)
        try:
            encoded = ""
            for line in self._read_zdj(path):
                if line and not line.startswith("#"):
                    encoded += line.strip()
            decoded = decode_text(encoded)

            self.current_file = path
            self.filename_var.set(os.path.splitext(name)[0])
            self.plain_text.delete("1.0", tk.END)
            self.plain_text.insert("1.0", decoded)
            self.update_status(f"已加载: {name}")
        except Exception as e:
            messagebox.showerror("错误", f"编辑失败: {e}")

    def delete_selected(self):
        sel = self.file_listbox.curselection()
        if not sel:
            return
        name = self.file_listbox.get(sel[0])
        if messagebox.askyesno("确认", f"确定删除 {name}？"):
            try:
                os.remove(os.path.join(self.current_folder, name))
                self.refresh_file_list()
                self.update_status(f"已删除: {name}")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败: {e}")


def main():
    root = tk.Tk()
    app = ZDJEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()