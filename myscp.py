import threading
import time
import tkinter as tk
from tkinter import filedialog
import paramiko
import json
import traceback
import queue
import os

class Color:
    GREEN = "green"
    RED = 'red'


class MessageOutPut:
    """
    消息
    """
    output_queue = queue.Queue()

    # 创建一个标志位，用于控制线程的运行状态
    output_thread_running = True

    output_thread = None

    @classmethod
    def process_output_queue(cls, main):
        
        text_color = {
            Color.GREEN:main.output_text.tag_config(Color.GREEN, foreground=Color.GREEN),
            Color.RED:main.output_text.tag_config(Color.RED, foreground=Color.RED),
        }
        while cls.output_thread_running:
            if not cls.output_queue.empty():
                message = cls.output_queue.get()
                color = message[1]
                clear = message[2]
                index = tk.END
                if clear:
                    # 获取最后一行的索引
                    last_line_index = main.output_text.index('end-1c linestart')
                    start_index = f"{str(int(last_line_index.split('.')[0])-1)}.0"
                    end_index =f"{str(int(last_line_index.split('.')[0]))}.0"
                    # 删除最后一行
                    main.output_text.delete(start_index, end_index)
                    index = start_index
                if color in text_color:
                    main.output_text.insert(index, str(message[0]) + "\n",color)
                else:
                    main.output_text.insert(index, str(message[0]) + "\n")
                main.output_text.see(tk.END)
            time.sleep(0.01)

    @classmethod
    def start_output_thread(cls, main):
        # 创建并启动输出线程
        cls.output_thread = threading.Thread(target=cls.process_output_queue, args=(main,))
        cls.output_thread.daemon = True
        cls.output_thread.start()

    @classmethod
    def stop_output_thread(cls):
        cls.output_thread_running = False

    @classmethod
    def put(cls, message,color=None,clear = False):

        cls.output_queue.put([message,color,clear]) 
    
    @classmethod
    def get_insert_index(cls,main):
        return main.output_text.index("end -2l linestart")


class Main:
    """
    主界面
    """

    def __init__(self):
        self.conf = "./ssh_commands.json"
        # 创建界面
        self.root = tk.Tk()
        self.root.title("SCP文件传输工具")

        # 初始化组件
        self.init_label()
        
        # 初始化消息体
        self.message_class = MessageOutPut
        self.message_class.start_output_thread(self)

        # 初始化ssh配置文件
        self.load_ssh_connections()

        # 取消上传/下载
        self.cancelled = False

        self.uploader = Upload(self)

        self.downloader = DowdLoad(self)

    def __del__(self):
        self.message_class.stop_output_thread()

    def init_label(self):
        """
        初始化界面布局
        """
        # 选择本地文件
        local_file_label = tk.Label(self.root, text="本地文件:")
        local_file_label.grid(row=0, column=0, sticky=tk.W)
        self.local_file_entry = tk.Entry(self.root)
        self.local_file_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")
        # 选择文件
        select_local_file_button = tk.Button(self.root, text="选择文件", command=self.select_local_file)
        select_local_file_button.grid(row=0, column=2, padx=5, pady=5, sticky="we")
        # 选择本地文件夹按钮
        select_local_directory_button = tk.Button(self.root, text="选择文件夹", command=self.select_local_directory)
        select_local_directory_button.grid(row=0, column=3, padx=5, pady=5, sticky="we")
        # 选择SSH连接
        ssh_connections_label = tk.Label(self.root, text="SSH连接:")
        ssh_connections_label.grid(row=1, column=0, sticky=tk.W)
        self.ssh_connections_listbox = tk.Listbox(self.root)
        self.ssh_connections_listbox.grid(row=1, column=1, padx=5, pady=5, sticky="we")
        select_ssh_connection_button = tk.Button(self.root, text="选择连接", command=self.select_ssh_connection)
        select_ssh_connection_button.grid(row=1, column=2, padx=5, pady=5, sticky="we")

        # 远程文件路径
        remote_file_label = tk.Label(self.root, text="远程文件:")
        remote_file_label.grid(row=2, column=0, sticky=tk.W)
        self.remote_file_entry = tk.Entry(self.root)
        self.remote_file_entry.grid(row=2, column=1, padx=5, pady=5, sticky="we")

        # 主机名、PEM路径和密码
        hostname_label = tk.Label(self.root, text="主机名:")
        hostname_label.grid(row=3, column=0, sticky=tk.W)
        self.hostname_entry = tk.Entry(self.root)
        self.hostname_entry.grid(row=3, column=1, padx=5, pady=5, sticky="we")
        pem_label = tk.Label(self.root, text="PEM路径:")
        pem_label.grid(row=4, column=0, sticky=tk.W)
        self.pem_entry = tk.Entry(self.root)
        self.pem_entry.grid(row=4, column=1, padx=5, pady=5, sticky="we")
        password_label = tk.Label(self.root, text="密码:")
        password_label.grid(row=5, column=0, sticky=tk.W)
        self.password_entry = tk.Entry(self.root, show="*")
        self.password_entry.grid(row=5, column=1, padx=5, pady=5, sticky="we")

        output_label = tk.Label(self.root, text="输出:")
        output_label.grid(row=7, column=0, sticky=tk.W)
        self.output_text = tk.Text(self.root, width=50, height=10)
        self.output_text.grid(row=7, column=1, columnspan=2, padx=5, pady=5, sticky="we")
        # 取消按钮
        cancel_button = tk.Button(self.root, text="取消", command=self.cancel_operation)
        cancel_button.grid(row=6, column=2, padx=5, pady=10)
        # 设置列的调整权重，使其在界面拉伸时自动调整大小
        self.root.columnconfigure(1, weight=1)
        # 设置行的调整权重，使其在界面拉伸时自动调整大小
        self.root.rowconfigure(2, weight=1)

    def init_upload(self, upload_func):
        """
        初始化上传按钮
        """
        upload_button = tk.Button(self.root, text="上传", command=upload_func)
        upload_button.grid(row=6, column=0, padx=5, pady=10)

    def init_download(self, download_func):
        """
        初始化下载按钮
        """
        download_button = tk.Button(self.root, text="下载", command=download_func)
        download_button.grid(row=6, column=1, padx=5, pady=10)

    def load_ssh_connections(self):
        """
        初始化连接配置
        """
        try:
            with open(self.conf, "r") as file:
                self.ssh_connections = json.load(file)
                self.ssh_connections_listbox.delete(0, tk.END)
                for name, connection in self.ssh_connections.items():
                    self.ssh_connections_listbox.insert(tk.END, name)
        except Exception as e:
            self.message_class.put(f"加载SSH连接出错：{str(e)}")

    def run(self):
        # 运行界面
        self.root.mainloop()
        # self.process_output_queue()
        # self.root.after(100, process_output_queue, self)

    def select_local_directory(self):
        """
        加载文件夹
        """
        local_directory_path = filedialog.askdirectory()
        self.local_file_entry.delete(0, tk.END)
        self.local_file_entry.insert(0, local_directory_path)

    def select_local_file(self):
        """
        加载文件
        """
        local_file_path = filedialog.askopenfilename()
        self.local_file_entry.delete(0, tk.END)
        self.local_file_entry.insert(0, local_file_path)

    def select_ssh_connection(self):
        """
        选择连接
        """
        selected_ssh_connection = self.ssh_connections_listbox.get(tk.ACTIVE)
        ssh_connection = self.ssh_connections[selected_ssh_connection]
        self.hostname_entry.delete(0, tk.END)
        self.hostname_entry.insert(0, ssh_connection["host"])
        if "pem" in ssh_connection:
            self.pem_entry.delete(0, tk.END)
            self.pem_entry.insert(0, ssh_connection["pem"])
        if "password" in ssh_connection:
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, ssh_connection["password"])

        try:
            host = ssh_connection["host"].split("@")[0]
        except Exception:
            self.message_class.put("check host error:")
            self.message_class.put(traceback.format_exc())
            host = ""
        self.remote_file_entry.delete(0, tk.END)
        self.remote_file_entry.insert(0, f"/home/{host}/")  # 设置默认值

    def cancel_operation(self):
        self.cancelled = True


class SftpConnect:
    """
    文件系统链接
    """

    def __init__(self, main: Main):
        self.main = main

    def init_sftp(self, host, pem=None, password=None):
        """
        初始化sftp
        """
        username = host.split("@")[0]
        hostname = host.split("@")[1]
        transport = paramiko.Transport((hostname, 22))
        self.main.message_class.put(f"Connecting to {hostname}...",Color.GREEN)
        if pem:
            transport.connect(username=username, pkey=paramiko.RSAKey.from_private_key_file(pem))
        else:
            transport.connect(username=username, password=password)
        self.main.message_class.put("Connected Success.",Color.GREEN)
        sftp = paramiko.SFTPClient.from_transport(transport)
        return sftp, transport


class Upload(SftpConnect): 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main.init_upload(self.upload_file)

    def scp_upload_file(self, local_path, remote_path, sftp):
        """
        上传文件
        """
        first_call = [True]  
        try:
            if self.main.cancelled:
                self.main.message_class.put("操作已取消",Color.RED)
                return
            self.main.message_class.put(f"Uploading {local_path} to {remote_path}...")
            # 获取插入进度信息的索引位置
            sftp.put(local_path, remote_path, callback=  lambda transferred, total: self.upload_progress(transferred, total,first_call))
            self.main.message_class.put("File upload completed.")
        except Exception:
            self.main.message_class.put("File upload failed:")
            self.main.message_class.put(traceback.format_exc(),Color.RED)

    def upload_progress(self, transferred, total,first_call):
        """
        上传进度
        """
        percentage = (transferred / total) * 100
        if not first_call[0]:
            self.main.message_class.put(f"Progress: {transferred}/{total} bytes ({percentage:.2f}%)",None,True)
            return
        first_call[0] = False
        self.main.message_class.put(f"Progress: {transferred}/{total} bytes ({percentage:.2f}%)")

    def upload_file_thread(self):
        """
        上传文件 线程
        """
        local_path = self.main.local_file_entry.get()
        remote_path = self.main.remote_file_entry.get()
        hostname = self.main.hostname_entry.get()
        pem = self.main.pem_entry.get()
        password = self.main.password_entry.get()

        sftp, transport = self.init_sftp(hostname, pem=pem, password=password)

        if os.path.isfile(local_path):
            filename = local_path.split("/")[-1]
            remote_file = os.path.join(remote_path, filename)
            self.scp_upload_file(local_path, remote_file, sftp)

        elif os.path.isdir(local_path):
            self.upload_directory(local_path, remote_path, sftp)
        else:
            self.main.message_class.put("Invalid local path.",Color.RED)
        self.main.message_class.put("Upload Finish !",Color.GREEN)
        self.main.cancelled = False
        transport.close()

    def create_remote_directory(self, remote_directory, sftp):
        """
        创建目录
        """
        try:
            sftp.stat(remote_directory)
        except FileNotFoundError:
            sftp.mkdir(remote_directory)

    def upload_directory(self, local_directory, remote_directory, sftp):
        """
        上传文件夹
        """

        self.create_remote_directory(remote_directory, sftp)

        base_directory = os.path.basename(local_directory)
        remote_directory = os.path.join(remote_directory, base_directory)

        self.create_remote_directory(remote_directory, sftp)

        for root, dirs, files in os.walk(local_directory):
            for file in files:
                if self.main.cancelled:
                    self.main.message_class.put("操作已取消",Color.RED)
                    return
                local_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_path, local_directory)
                remote_path = os.path.normpath(os.path.join(remote_directory, relative_path))

                remote_path = remote_path.replace("\\", "/")

                self.scp_upload_file(local_path, remote_path, sftp)

            for directory in dirs:
                local_subdirectory = os.path.join(root, directory)
                relative_subdirectory = os.path.relpath(local_subdirectory, local_directory)
                remote_subdirectory = os.path.normpath(os.path.join(remote_directory, relative_subdirectory))

                remote_subdirectory = remote_subdirectory.replace("\\", "/")

                self.create_remote_directory(remote_subdirectory, sftp)

                self.upload_directory(local_subdirectory, remote_subdirectory, sftp)

    def upload_file(self):
        """
        上传文件按钮
        """
        upload_thread = threading.Thread(target=self.upload_file_thread)
        upload_thread.start()


class DowdLoad(SftpConnect):
    """
    下载
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main.init_download(self.download_file)

    def scp_download_thread(self, remote_path, local_path, hostname, pem=None, password=None):
        """
        下载线程
        """

        sftp, transport = self.init_sftp(hostname, pem=pem, password=password)
        try:
            self.main.message_class.put(f"start download  {remote_path}...")
            if sftp.stat(remote_path).st_mode & 0o40000:
                local_path = os.path.join(local_path, os.path.split(remote_path.rstrip('/'))[-1])
                self.scp_download_directory(remote_path, local_path, sftp)
            else:
                local_path = os.path.join(local_path, os.path.basename(remote_path))
                self.scp_download_file(remote_path, local_path, sftp)
        except Exception as e:
            self.main.message_class.put(f"File download failed: {e}")
            traceback.print_exc()
        else:
            self.main.message_class.put("File download completed successfully",Color.GREEN)
        finally:
            transport.close()

    def download_file(self):
        """
        下载按钮点击
        """
        remote_path = self.main.remote_file_entry.get()
        local_path = self.main.local_file_entry.get()
        hostname = self.main.hostname_entry.get()
        pem = self.main.pem_entry.get()
        password = self.main.password_entry.get()
        threading.Thread(target=self.scp_download_thread, args=(remote_path, local_path, hostname),
                         kwargs={"pem": pem, "password": password}).start()

    def scp_download_directory(self, remote_directory, local_directory, sftp):
        """
        下载文件夹
        """
        # 创建本地文件夹
        os.makedirs(local_directory, exist_ok=True)
        # 递归下载文件夹中的文件和子文件夹
        self.download_files_recursively(remote_directory, local_directory, sftp)
        self.main.message_class.put("Directory download completed successfully")

    def scp_download_file(self, remote_path, local_path, sftp):
        """
        下载单个文件
        """
        sftp.get(remote_path, local_path, callback=lambda x, y: self.main.message_class.put(f"Downloaded {x}/{y} bytes"))

    def download_files_recursively(self, remote_directory, local_directory, sftp):
        """
        下载文件夹下所有内容
        """
        files = sftp.listdir(remote_directory)
        for file in files:
            remote_path = os.path.join(remote_directory, file)
            if sftp.stat(remote_path).st_mode & 0o40000:
                new_local_directory = os.path.join(local_directory, file)
                os.makedirs(new_local_directory, exist_ok=True)
                self.download_files_recursively(remote_path, new_local_directory, sftp)
            else:
                remote_relative_path = os.path.relpath(remote_path, remote_directory)
                local_file_path = os.path.join(local_directory, remote_relative_path)
                local_file_directory = os.path.dirname(local_file_path)
                os.makedirs(local_file_directory, exist_ok=True)
                self.main.message_class.put(f"Downloading {remote_path} to {local_file_path}...")
                self.scp_download_file(remote_path, local_file_path, sftp)


Main().run()
