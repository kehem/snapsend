import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.properties import ListProperty, ObjectProperty, StringProperty, NumericProperty
from kivy.core.window import Window
import socket
import threading
import time
import tkinter as tk
from tkinter import filedialog
import os
from kivy.graphics import Color, RoundedRectangle, Rectangle
import zipfile
import tempfile


kivy.require('2.0.0')

Window.clearcolor = (1, 1, 1, 1)  # Set white background


import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)


class SendingStatus(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [10, 10]
        self.size_hint = (1, None)
        self.height = 120
        self.spacing = 5
        
        with self.canvas.before:
            Color(0.9, 0.95, 1, 1)  # Light blue background
            self.rect = RoundedRectangle(radius=[10], pos=self.pos, size=self.size)
            self.bind(pos=self.update_rect, size=self.update_rect)

        self.status_label = Label(
            text="Sending to Device...",
            font_name=resource_path('fonts/K2D-ExtraBold.ttf'),
            font_size=18,
            color=(0, 0, 0, 1)
        )
        self.file_name_label = Label(
            text="",
            font_name=resource_path('fonts/K2D-ExtraBold.ttf'),
            font_size=16,
            color=(0, 0, 0, 1)
        )
        self.progress_bar = ProgressBar(max=100, value=0)
        self.speed_label = Label(
            text="0 MB/s",
            font_name=resource_path('fonts/K2D-ExtraBold.ttf'),
            font_size=14,
            color=(0.2, 0.2, 0.2, 1)
        )

        self.add_widget(self.status_label)
        self.add_widget(self.file_name_label)
        self.add_widget(self.progress_bar)
        self.add_widget(self.speed_label)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def update_progress(self, value, speed="0 MB/s"):
        self.progress_bar.value = value
        self.speed_label.text = speed

    def set_file_info(self, filename, device_name):
        self.file_name_label.text = filename
        self.status_label.text = f"Sending to {device_name}..."

class DeviceCard(BoxLayout):
    def __init__(self, name, ip, screen_manager, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [10, 10]
        self.size_hint_y = None
        self.height = 100
        self.spacing = 5
        self.name = name
        self.ip = ip
        self.screen_manager = screen_manager
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.93, 0.95, 0.98, 1)
            self.rect = RoundedRectangle(radius=[10], pos=self.pos, size=self.size)
            self.bind(pos=self.update_rect, size=self.update_rect)

        self.name_label = Label(text=f"[b]{name}[/b]", markup=True, font_size=25, font_name=resource_path('fonts/K2D-ExtraBold.ttf'), color=(0, 0, 0, 1))
        self.ip_label = Label(text=ip, font_name=resource_path('fonts/K2D-ExtraBold.ttf'), font_size=14, color=(0.2, 0.2, 0.2, 1))

        self.add_widget(self.name_label)
        self.add_widget(self.ip_label)
        self.bind(on_touch_down=self.on_card_touch)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_card_touch(self, instance, touch):
        if self.collide_point(*touch.pos):
            self.screen_manager.current = 'upload'
            upload_screen = self.screen_manager.get_screen('upload')
            upload_screen.set_device_info(self.name, self.ip)

class FileTransferManager:
    @staticmethod
    def create_zip_from_folder(folder_path):
        """Create a temporary zip file from a folder with optimized compression"""
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.close()
        
        # Use ZIP_STORED (no compression) for maximum speed on LAN
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_STORED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)
        
        return temp_zip.name

    @staticmethod
    def send_file(file_path, target_ip, progress_callback=None, completion_callback=None):
        """Send a file to target IP address with maximum speed optimization"""
        def send_thread():
            try:
                # Create socket connection with optimization
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                # Socket optimizations for maximum speed
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's algorithm
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)  # 1MB send buffer
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)  # 1MB receive buffer
                
                sock.settimeout(30)  # 30 second timeout
                sock.connect((target_ip, 32769))
                
                # Get file info
                file_size = os.path.getsize(file_path)
                file_name = os.path.basename(file_path)
                
                # Send file info first
                file_info = f"{file_name}|{file_size}".encode()
                sock.send(file_info)
                
                # Wait for acknowledgment
                ack = sock.recv(3)
                if ack != b'ACK':
                    raise Exception("No acknowledgment received")
                
                # Send file data with larger buffer for maximum speed
                sent_size = 0
                start_time = time.time()
                last_update = start_time
                buffer_size = 1048576  # 1MB buffer for maximum LAN speed
                
                with open(file_path, 'rb') as f:
                    while sent_size < file_size:
                        data = f.read(buffer_size)
                        if not data:
                            break
                        
                        # Send all data (handle partial sends)
                        bytes_sent = 0
                        while bytes_sent < len(data):
                            n = sock.send(data[bytes_sent:])
                            if n == 0:
                                raise Exception("Connection broken")
                            bytes_sent += n
                        
                        sent_size += len(data)
                        
                        # Update progress less frequently for better performance
                        current_time = time.time()
                        if current_time - last_update >= 0.1:  # Update every 100ms
                            progress = (sent_size / file_size) * 100
                            elapsed_time = current_time - start_time
                            if elapsed_time > 0:
                                speed_bytes = sent_size / elapsed_time
                                speed_mb = speed_bytes / (1024 * 1024)
                                speed_text = f"{speed_mb:.1f} MB/s"
                            else:
                                speed_text = "0 MB/s"
                            
                            # Update progress
                            if progress_callback:
                                Clock.schedule_once(lambda dt, p=progress, s=speed_text: progress_callback(p, s))
                            
                            last_update = current_time
                
                # Final progress update
                if progress_callback:
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        speed_bytes = file_size / elapsed_time
                        speed_mb = speed_bytes / (1024 * 1024)
                        speed_text = f"{speed_mb:.1f} MB/s"
                    else:
                        speed_text = "0 MB/s"
                    Clock.schedule_once(lambda dt: progress_callback(100, speed_text))
                
                sock.close()
                
                # Clean up temporary zip files
                if file_path.endswith('.zip') and 'temp' in file_path:
                    try:
                        os.unlink(file_path)
                    except:
                        pass
                
                if completion_callback:
                    Clock.schedule_once(lambda dt: completion_callback(True, "File sent successfully"))
                    
            except Exception as e:
                if completion_callback:
                    Clock.schedule_once(lambda dt: completion_callback(False, str(e)))
        
        threading.Thread(target=send_thread, daemon=True).start()

class DeviceDiscoveryScreen(Screen):
    discovered_devices = ListProperty([])

    def __init__(self, screen_manager, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = screen_manager
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Top Bar
        top_bar = BoxLayout(size_hint_y=None, height=60, padding=[10, 0], spacing=10)
        label = Label(
            text='[b]SnapSend[/b]',
            markup=True,
            font_name=resource_path('fonts/K2D-ExtraBold.ttf'),
            font_size=28,
            color=(0.2, 0.4, 0.7, 1),
            valign='middle'
        )
        label.bind(size=label.setter('text_size'))
        top_bar.add_widget(label)
        top_bar.add_widget(Widget())
        img_box = BoxLayout(orientation='vertical', size_hint=(None, 1), width=30)
        img = Image(source='settings_icon.png', size_hint=(1, None), size=(30, 30), allow_stretch=True)
        img_box.add_widget(Widget())  # Spacer to push image to center
        img_box.add_widget(img)
        img_box.add_widget(Widget())  # Spacer to push image to center
        top_bar.add_widget(img_box)
        self.layout.add_widget(top_bar)

        # ScrollView for Devices
        self.device_scroll = ScrollView()
        self.device_grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.device_grid.bind(minimum_height=self.device_grid.setter('height'))
        self.device_scroll.add_widget(self.device_grid)
        self.layout.add_widget(self.device_scroll)

        self.add_widget(self.layout)

        # Start threads
        threading.Thread(target=self.listen_for_devices, daemon=True).start()
        threading.Thread(target=self.broadcast_device_name, daemon=True).start()
        threading.Thread(target=self.listen_for_files, daemon=True).start()

    def add_device(self, name, ip):
        entry = f"{name}|{ip}"
        if entry not in self.discovered_devices:
            self.discovered_devices.append(entry)
            Clock.schedule_once(lambda dt: self.update_ui(name, ip))

    def update_ui(self, name, ip):
        card = DeviceCard(name, ip, self.screen_manager)
        self.device_grid.add_widget(card)

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "0.0.0.0"

    def broadcast_device_name(self):
        name = "Anirban Singha"
        ip = self.get_local_ip()
        msg = f"{name}|{ip}".encode()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            try:
                sock.sendto(msg, ("<broadcast>", 32768))
            except Exception as e:
                print("Broadcast error:", e)
            time.sleep(2)

    def listen_for_devices(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", 32768))
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                decoded = data.decode()
                if "|" in decoded:
                    name, ip = decoded.split("|")
                    self.add_device(name, ip)
            except Exception as e:
                print("Listen error:", e)

    def listen_for_files(self):
        # Optimized file receiving server for maximum speed
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Socket optimizations for maximum receive speed
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's algorithm
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)  # 1MB receive buffer
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)  # 1MB send buffer
            
            sock.bind(('', 32769))
            sock.listen(10)  # Increased backlog for better performance
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads", "SnapSend")
            os.makedirs(downloads_path, exist_ok=True)

            while True:
                try:
                    client_socket, addr = sock.accept()
                    
                    # Apply same optimizations to client socket
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)
                    
                    # Handle file reception in a separate thread for better performance
                    threading.Thread(target=self.handle_file_reception, 
                                   args=(client_socket, addr, downloads_path), 
                                   daemon=True).start()
                    
                except Exception as e:
                    print("File receive error:", e)
        except Exception as e:
            print("Listen server error:", e)

    def handle_file_reception(self, client_socket, addr, downloads_path):
        """Handle individual file reception with optimizations"""
        try:
            file_info = client_socket.recv(1024).decode()
            file_name = file_info.split('|')[0]
            file_size = int(file_info.split('|')[1])
            
            # Send acknowledgment
            client_socket.send(b'ACK')
            
            print(f"Receiving {file_name} ({file_size} bytes) from {addr[0]}")
            
            file_path = os.path.join(downloads_path, file_name)
            
            # Use larger buffer and direct file writing for maximum speed
            buffer_size = 1048576  # 1MB buffer
            received_size = 0
            start_time = time.time()
            
            with open(file_path, 'wb') as f:
                while received_size < file_size:
                    remaining = file_size - received_size
                    chunk_size = min(buffer_size, remaining)
                    
                    data = b''
                    while len(data) < chunk_size:
                        packet = client_socket.recv(chunk_size - len(data))
                        if not packet:
                            break
                        data += packet
                    
                    if not data:
                        break
                    
                    f.write(data)
                    received_size += len(data)
            
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                speed_mb = (file_size / (1024 * 1024)) / elapsed_time
                print(f"Successfully received {file_name} at {speed_mb:.1f} MB/s")
            else:
                print(f"Successfully received {file_name}")
                
            client_socket.close()
            
        except Exception as e:
            print(f"Error handling file reception: {e}")
            client_socket.close()

class UploadScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.device_name = ""
        self.device_ip = ""
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Top Bar
        top_bar = BoxLayout(size_hint_y=None, height=60, padding=[10, 0], spacing=10)
        label = Label(
            text='[b]SnapSend[/b]',
            markup=True,
            font_name=resource_path('fonts/K2D-ExtraBold.ttf'),
            font_size=28,
            color=(0.2, 0.4, 0.7, 1),
            valign='middle'
        )
        label.bind(size=label.setter('text_size'))
        top_bar.add_widget(label)
        top_bar.add_widget(Widget())
        img_box = BoxLayout(orientation='vertical', size_hint=(None, 1), width=30)
        img = Image(source=resource_path('back.png'), size_hint=(1, None), size=(30, 30), allow_stretch=True)
        img_box.add_widget(Widget())  # Spacer to push image to center
        img_box.add_widget(img)
        img_box.add_widget(Widget())  # Spacer to push image to center
        top_bar.add_widget(img_box)
        self.layout.add_widget(top_bar)

        # User Info
        self.user_info = BoxLayout(size_hint_y=None, height=40, padding=[10, 0])
        self.name_label = Label(text="[b]Select a device[/b]", markup=True, font_name=resource_path('fonts/K2D-ExtraBold.ttf'), font_size=18, color=(0, 0, 0, 1))
        self.ip_label = Label(text="", font_name=resource_path('fonts/K2D-ExtraBold.ttf'), font_size=14, color=(0.2, 0.2, 0.2, 1))
        self.user_info.add_widget(self.name_label)
        self.user_info.add_widget(Widget())  # Spacer
        self.user_info.add_widget(self.ip_label)
        self.layout.add_widget(self.user_info)

        # Sending Status (initially hidden)
        self.sending_status = SendingStatus()
        self.sending_status.opacity = 0
        self.layout.add_widget(self.sending_status)

        # Upload Area Container
        self.upload_container = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.upload_area = BoxLayout(orientation='vertical', size_hint=(1, None), height=500, padding=20)
        with self.upload_area.canvas:
            Color(0.9, 0.95, 1, 1)  # Light blue background
            self.upload_area.rect = Rectangle(pos=self.upload_area.pos, size=self.upload_area.size)
            self.upload_area.bind(pos=self.update_rect, size=self.update_rect)

        self.upload_label = Label(text="Drag and drop file/folder\nor\nClick to select files/folder", halign='center', valign='middle', font_name=resource_path('fonts/K2D-ExtraBold.ttf'), font_size=16, color=(0.2, 0.2, 0.2, 1))
        self.upload_label.bind(size=self.upload_label.setter('text_size'))
        self.upload_area.add_widget(self.upload_label)
        self.upload_container.add_widget(self.upload_area)
        self.layout.add_widget(self.upload_container)

        self.add_widget(self.layout)
        self.bind(size=self.adjust_layout)

    def update_rect(self, instance, value):
        self.upload_area.rect.pos = self.upload_area.pos
        self.upload_area.rect.size = self.upload_area.size

    def adjust_layout(self, instance, value):
        remaining_height = self.height - (60 + 40 + 20)  # Top bar + User info + padding
        if remaining_height > 0:
            self.upload_area.height = min(remaining_height, 400)  # Cap at 400 or use remaining height
        self.upload_container.pos_hint = {'center_y': 0.5}

    def set_device_info(self, name, ip):
        self.device_name = name
        self.device_ip = ip
        self.name_label.text = f"[b]{name}[/b]"
        self.ip_label.text = ip

    def on_touch_down(self, touch):
        if self.upload_area.collide_point(*touch.pos):
            self.show_upload_dialog()

    def on_drop_file(self, window, file_path, x, y):
        # Convert window coordinates to local coordinates relative to upload_area
        upload_area_pos = self.upload_area.to_widget(0, 0, relative=True)
        upload_area_size = self.upload_area.size

        # Check if the drop is within the upload_area
        if (0 <= x - upload_area_pos[0] <= upload_area_size[0] and
            0 <= y - upload_area_pos[1] <= upload_area_size[1]):
            file_path_str = file_path.decode('utf-8')
            self.handle_file_selection([file_path_str])

    def show_upload_dialog(self):
        # Use tkinter to open Windows File Explorer
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Allow both files and folders
        file_paths = filedialog.askopenfilenames(title="Select Files", filetypes=[("All files", "*.*")])
        if not file_paths:
            # If no files selected, try folder selection
            folder_path = filedialog.askdirectory(title="Select Folder")
            if folder_path:
                file_paths = [folder_path]
        
        root.destroy()

        if file_paths:
            self.handle_file_selection(file_paths)

    def handle_file_selection(self, file_paths):
        if not file_paths or not self.device_ip:
            return
        
        for file_path in file_paths:
            if os.path.isfile(file_path):
                # Send file directly
                self.send_file(file_path)
            elif os.path.isdir(file_path):
                # Create zip and send
                self.send_folder(file_path)

    def send_file(self, file_path):
        """Send a single file"""
        filename = os.path.basename(file_path)
        self.show_sending_status(filename)
        
        FileTransferManager.send_file(
            file_path,
            self.device_ip,
            progress_callback=self.update_sending_progress,
            completion_callback=self.on_send_complete
        )

    def send_folder(self, folder_path):
        """Send a folder by creating a zip file"""
        folder_name = os.path.basename(folder_path)
        zip_filename = f"{folder_name}.zip"
        self.show_sending_status(zip_filename)
        
        def create_and_send():
            try:
                # Create temporary zip
                temp_zip_path = FileTransferManager.create_zip_from_folder(folder_path)
                
                # Send the zip file
                FileTransferManager.send_file(
                    temp_zip_path,
                    self.device_ip,
                    progress_callback=self.update_sending_progress,
                    completion_callback=self.on_send_complete
                )
            except Exception as e:
                Clock.schedule_once(lambda dt: self.on_send_complete(False, str(e)))
        
        threading.Thread(target=create_and_send, daemon=True).start()

    def show_sending_status(self, filename):
        """Show the sending status UI"""
        self.sending_status.set_file_info(filename, self.device_name)
        self.sending_status.opacity = 1
        self.sending_status.update_progress(0)

    def update_sending_progress(self, progress, speed):
        """Update sending progress"""
        if self.sending_status.opacity == 1:
            self.sending_status.update_progress(progress, speed)

    def on_send_complete(self, success, message):
        """Handle send completion"""
        self.sending_status.opacity = 0
        if success:
            print("File sent successfully!")
        else:
            print(f"Send failed: {message}")

class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')
        label = Label(text="SnapSend", font_size=76, color=(0.2, 0.4, 0.7, 1), font_name=resource_path('fonts/K2D-ExtraBold.ttf'), halign="center", valign="middle")
        label.bind(size=label.setter('text_size'))
        layout.add_widget(label)
        self.add_widget(layout)

class SnapSendApp(App):
    def build(self):
        Window.size = (400, 700)
        self.icon = resource_path('logo.svg')
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(DeviceDiscoveryScreen(screen_manager=sm, name='devices'))
        upload_screen = UploadScreen(name='upload')
        sm.add_widget(upload_screen)

        def on_drop_file(window, file_path, x, y):
            current_screen = sm.current_screen
            if current_screen and hasattr(current_screen, 'on_drop_file'):
                current_screen.on_drop_file(window, file_path, x, y)

        Window.bind(on_drop_file=on_drop_file)
        Clock.schedule_once(lambda dt: setattr(sm, 'current', 'devices'), 3)
        return sm


if __name__ == '__main__':
    SnapSendApp().run()