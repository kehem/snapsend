import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.properties import ListProperty, StringProperty, ObjectProperty, NumericProperty
from kivy.core.window import Window
from kivy.graphics import Line, Color, Rectangle, Ellipse
from kivy.uix.relativelayout import RelativeLayout
import socket
import threading
import time
import tkinter as tk
from tkinter import filedialog
import os
import zipfile
import tempfile
import sys
from collections import deque
import platform
from kivy.lang import Builder


kivy.require('2.0.0')
Window.clearcolor = (1, 1, 1, 1)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# Load the KV file
# Builder.load_file(resource_path('snapsend.kv'))


class SpeedGraphWidget(Widget):
    """Custom widget to display transfer speed graph"""
    max_speed = NumericProperty(1.0)  # MB/s
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.speed_history = deque(maxlen=50)  # Keep last 50 speed measurements
        self.bind(size=self.update_graph, pos=self.update_graph)
        
    def add_speed_point(self, speed_mbps):
        """Add a new speed measurement to the graph"""
        self.speed_history.append(speed_mbps)
        if speed_mbps > self.max_speed:
            self.max_speed = speed_mbps * 1.2  # Add 20% headroom
        self.update_graph()
        
    def update_graph(self, *args):
        """Redraw the speed graph"""
        self.canvas.clear()
        
        if not self.speed_history or self.width <= 0 or self.height <= 0:
            return
            
        with self.canvas:
            # Background
            Color(0.95, 0.95, 0.95, 1)
            Rectangle(pos=self.pos, size=self.size)
            
            # Grid lines
            Color(0.8, 0.8, 0.8, 1)
            grid_lines = 5
            for i in range(grid_lines + 1):
                y = self.y + (self.height / grid_lines) * i
                Line(points=[self.x, y, self.x + self.width, y], width=1)
                
            # Speed curve
            if len(self.speed_history) > 1:
                Color(0.2, 0.6, 1.0, 1)  # Blue color for speed line
                
                points = []
                for i, speed in enumerate(self.speed_history):
                    x = self.x + (self.width / (len(self.speed_history) - 1)) * i
                    y = self.y + (speed / max(self.max_speed, 0.1)) * self.height
                    points.extend([x, y])
                    
                if len(points) >= 4:  # Need at least 2 points
                    Line(points=points, width=2)
                    
                # Add dots for recent points
                Color(0.1, 0.4, 0.8, 1)
                for i, speed in enumerate(list(self.speed_history)[-10:]):  # Last 10 points
                    idx = len(self.speed_history) - 10 + i
                    if idx >= 0:
                        x = self.x + (self.width / (len(self.speed_history) - 1)) * idx
                        y = self.y + (speed / max(self.max_speed, 0.1)) * self.height
                        Ellipse(pos=(x-2, y-2), size=(4, 4))

class DeviceCard(BoxLayout):
    name = StringProperty()
    ip = StringProperty()
    
    screen_manager = ObjectProperty()
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.screen_manager.current = 'upload'
            upload_screen = self.screen_manager.get_screen('upload')
            upload_screen.set_device_info(self.name, self.ip)
        return super().on_touch_down(touch)

class FileTransferManager:
    @staticmethod
    def create_zip_from_folder(folder_path):
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.close()
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_STORED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arcname)
        return temp_zip.name

    @staticmethod
    def send_file(file_path, target_ip, progress_callback=None, completion_callback=None):
        def send_thread():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
                sock.settimeout(30)
                sock.connect((target_ip, 32769))
                
                file_size = os.path.getsize(file_path)
                file_name = os.path.basename(file_path)
                file_info = f"{file_name}|{file_size}".encode()
                sock.send(file_info)
                
                ack = sock.recv(3)
                if ack != b'ACK':
                    raise Exception("No acknowledgment received")
                
                sent_size = 0
                start_time = time.time()
                last_update = start_time
                buffer_size = 1048576
                
                # Speed calculation variables
                speed_history = deque(maxlen=10)  # Keep last 10 measurements for smoothing
                
                with open(file_path, 'rb') as f:
                    while sent_size < file_size:
                        chunk_start_time = time.time()
                        data = f.read(buffer_size)
                        if not data:
                            break
                            
                        bytes_sent = 0
                        while bytes_sent < len(data):
                            n = sock.send(data[bytes_sent:])
                            if n == 0:
                                raise Exception("Connection broken")
                            bytes_sent += n
                            
                        sent_size += len(data)
                        current_time = time.time()
                        
                        # Calculate instantaneous speed
                        chunk_time = current_time - chunk_start_time
                        if chunk_time > 0:
                            chunk_speed = len(data) / chunk_time / (1024 * 1024)  # MB/s
                            speed_history.append(chunk_speed)
                        
                        if current_time - last_update >= 0.1:  # Update every 100ms
                            progress = (sent_size / file_size) * 100
                            
                            # Calculate average speed from recent measurements
                            if speed_history:
                                avg_speed = sum(speed_history) / len(speed_history)
                                speed_text = f"{avg_speed:.1f} MB/s"
                            else:
                                avg_speed = 0
                                speed_text = "0 MB/s"
                            
                            if progress_callback:
                                Clock.schedule_once(
                                    lambda dt, p=progress, s=speed_text, sp=avg_speed: 
                                    progress_callback(p, s, sp)
                                )
                            last_update = current_time
                
                # Final update
                if progress_callback:
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        final_speed = file_size / elapsed_time / (1024 * 1024)
                        speed_text = f"{final_speed:.1f} MB/s"
                    else:
                        final_speed = 0
                        speed_text = "0 MB/s"
                    Clock.schedule_once(lambda dt: progress_callback(100, speed_text, final_speed))
                
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

    def __init__(self, screen_manager, app, **kwargs):
        super().__init__(**kwargs)
        self.screen_manager = screen_manager
        self.app = app
        self._last_seen = {}
        self._device_cards = {}  # Track device cards by entry
        threading.Thread(target=self.listen_for_devices, daemon=True).start()
        threading.Thread(target=self.broadcast_device_name, daemon=True).start()
        threading.Thread(target=self.listen_for_files, daemon=True).start()
        Clock.schedule_interval(self.check_device_timeouts, 2)

    def add_device(self, name, ip):
        entry = f"{name}|{ip}"
        if entry not in self.discovered_devices and entry not in self._device_cards:
            self.discovered_devices.append(entry)
            Clock.schedule_once(lambda dt: self.update_ui(name, ip))
        # Mark device as seen now
        self._last_seen[entry] = time.time()

    def update_ui(self, name, ip):
        entry = f"{name}|{ip}"
        # Prevent duplicate cards in UI
        if entry not in self._device_cards:
            card = DeviceCard(name=name, ip=ip, screen_manager=self.screen_manager)
            self.ids.device_grid.add_widget(card)
            self._device_cards[entry] = card

    def remove_device(self, entry):
        if entry in self.discovered_devices:
            self.discovered_devices.remove(entry)
        # Remove from UI
        card = self._device_cards.pop(entry, None)
        if card and card in self.ids.device_grid.children:
            self.ids.device_grid.remove_widget(card)

    def check_device_timeouts(self, dt):
        now = time.time()
        timeout = 6  # seconds
        for entry in list(self.discovered_devices):
            if entry not in self._last_seen or now - self._last_seen[entry] > timeout:
                self.remove_device(entry)
                self._last_seen.pop(entry, None)

    # (Remove this duplicate __init__ method entirely)

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
        # Try to get device name from environment or system
        try:
            name = platform.node()
            if not name:
                name = os.environ.get('COMPUTERNAME', '') or os.environ.get('HOSTNAME', '')
            if not name:
                name = "Unknown Device"
        except Exception:
            name = "Unknown Device"
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)
            sock.bind(('', 32769))
            sock.listen(10)
            
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads", "SnapSend")
            os.makedirs(downloads_path, exist_ok=True)
            
            while True:
                try:
                    client_socket, addr = sock.accept()
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)
                    threading.Thread(target=self.handle_file_reception, 
                                   args=(client_socket, addr, downloads_path), 
                                   daemon=True).start()
                except Exception as e:
                    print("File receive error:", e)
        except Exception as e:
            print("Listen server error:", e)

    def handle_file_reception(self, client_socket, addr, downloads_path):
        try:
            file_info = client_socket.recv(1024).decode()
            file_name = file_info.split('|')[0]
            file_size = int(file_info.split('|')[1])
            client_socket.send(b'ACK')
            
            print(f"Receiving {file_name} ({file_size} bytes) from {addr[0]}")
            Clock.schedule_once(lambda dt: self.app.show_receiving_popup(file_name, addr[0]))
            
            file_path = os.path.join(downloads_path, file_name)
            buffer_size = 1048576
            received_size = 0
            start_time = time.time()
            last_update = start_time
            
            # Speed calculation variables
            speed_history = deque(maxlen=10)
            
            with open(file_path, 'wb') as f:
                while received_size < file_size:
                    chunk_start_time = time.time()
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
                    current_time = time.time()
                    
                    # Calculate instantaneous speed
                    chunk_time = current_time - chunk_start_time
                    if chunk_time > 0:
                        chunk_speed = len(data) / chunk_time / (1024 * 1024)  # MB/s
                        speed_history.append(chunk_speed)
                    
                    if current_time - last_update >= 0.1:
                        progress = (received_size / file_size) * 100
                        
                        # Calculate average speed
                        if speed_history:
                            avg_speed = sum(speed_history) / len(speed_history)
                            speed_text = f"{avg_speed:.1f} MB/s"
                        else:
                            avg_speed = 0
                            speed_text = "0 MB/s"
                            
                        Clock.schedule_once(
                            lambda dt, p=progress, s=speed_text, sp=avg_speed: 
                            self.app.update_receiving_progress(p, s, sp)
                        )
                        last_update = current_time
            
            # Final update
            elapsed_time = time.time() - start_time
            if elapsed_time > 0:
                final_speed = (file_size / (1024 * 1024)) / elapsed_time
                speed_text = f"{final_speed:.1f} MB/s"
            else:
                final_speed = 0
                speed_text = "0 MB/s"
                
            Clock.schedule_once(lambda dt: self.app.update_receiving_progress(100, speed_text, final_speed))
            print(f"Successfully received {file_name}")
            Clock.schedule_once(lambda dt: self.app.close_receiving_popup(True, "File received successfully"))
            client_socket.close()
            
        except Exception as e:
            print(f"Error handling file reception: {e}")
            Clock.schedule_once(lambda dt: self.app.close_receiving_popup(False, str(e)))
            client_socket.close()



class UploadScreen(Screen):
    device_name = StringProperty("")
    device_ip = StringProperty("")
    sending_popup = None

    def set_device_info(self, name, ip):
        self.device_name = name
        self.device_ip = ip
        self.ids.name_label.text = f"[b]{name}[/b]"
        self.ids.ip_label.text = ip

    def go_to_devices(self):
        self.manager.current = 'devices'

    def on_back_button_touch(self, touch):
        if self.ids.back_button.collide_point(*touch.pos):
            self.go_to_devices()
            return True
        return False

    def on_touch_down(self, touch):
        if self.ids.upload_area.collide_point(*touch.pos):
            self.show_upload_dialog()
        return super().on_touch_down(touch)

    def on_drop_file(self, window, file_path, x, y):
        file_path_str = file_path.decode('utf-8')
        self.handle_file_selection([file_path_str])

    def show_upload_dialog(self):
        root = tk.Tk()
        root.withdraw()
        file_paths = filedialog.askopenfilenames(title="Select Files", filetypes=[("All files", "*.*")])
        if not file_paths:
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
                self.send_file(file_path)
            elif os.path.isdir(file_path):
                self.send_folder(file_path)

    def send_file(self, file_path):
        filename = os.path.basename(file_path)
        self.show_sending_popup(filename)
        FileTransferManager.send_file(
            file_path,
            self.device_ip,
            progress_callback=self.update_sending_progress,
            completion_callback=self.on_send_complete
        )

    def send_folder(self, folder_path):
        folder_name = os.path.basename(folder_path)
        zip_filename = f"{folder_name}.zip"
        self.show_sending_popup(zip_filename)
        
        def create_and_send():
            try:
                temp_zip_path = FileTransferManager.create_zip_from_folder(folder_path)
                FileTransferManager.send_file(
                    temp_zip_path,
                    self.device_ip,
                    progress_callback=self.update_sending_progress,
                    completion_callback=self.on_send_complete
                )
            except Exception as e:
                Clock.schedule_once(lambda dt: self.on_send_complete(False, str(e)))
                
        threading.Thread(target=create_and_send, daemon=True).start()

    def show_sending_popup(self, filename):
        if self.sending_popup:
            self.sending_popup.dismiss()
            
        self.sending_popup = Popup(
            content=SendingProgressPopup(),
            title="",
            size_hint=(0.85, None),
            height=280,  # Increased height for graph
            auto_dismiss=False
        )
        self.sending_popup.content.ids.file_name_label.text = filename
        self.sending_popup.content.ids.status_label.text = f"Sending to {self.device_name}..."
        self.sending_popup.content.ids.progress_bar.value = 0
        self.sending_popup.content.ids.speed_label.text = "0 MB/s"
        self.sending_popup.open()

    def update_sending_progress(self, progress, speed, speed_value=0):
        if self.sending_popup:
            self.sending_popup.content.ids.progress_bar.value = progress
            self.sending_popup.content.ids.speed_label.text = speed
            # Update speed graph
            if hasattr(self.sending_popup.content.ids, 'speed_graph'):
                self.sending_popup.content.ids.speed_graph.add_speed_point(speed_value)

    def on_send_complete(self, success, message):
        if self.sending_popup:
            self.sending_popup.dismiss()
            self.sending_popup = None
        if success:
            print("File sent successfully!")
        else:
            print(f"Send failed: {message}")

class SendingProgressPopup(BoxLayout):
    pass

class ReceivingProgressPopup(BoxLayout):
    pass

class SplashScreen(Screen):
    pass

class SnapSendApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.receiving_popup = None

    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.abspath(relative_path)

    def show_receiving_popup(self, filename, ip):
        if self.receiving_popup:
            self.receiving_popup.dismiss()
            
        self.receiving_popup = Popup(
            content=ReceivingProgressPopup(),
            title="",
            size_hint=(0.85, None),
            height=280,  # Increased height for graph
            auto_dismiss=False
        )
        self.receiving_popup.content.ids.file_name_label.text = filename
        self.receiving_popup.content.ids.status_label.text = f"Receiving from {ip}..."
        self.receiving_popup.content.ids.progress_bar.value = 0
        self.receiving_popup.content.ids.speed_label.text = "0 MB/s"
        self.receiving_popup.open()

    def update_receiving_progress(self, progress, speed, speed_value=0):
        if self.receiving_popup:
            self.receiving_popup.content.ids.progress_bar.value = progress
            self.receiving_popup.content.ids.speed_label.text = speed
            # Update speed graph
            if hasattr(self.receiving_popup.content.ids, 'speed_graph'):
                self.receiving_popup.content.ids.speed_graph.add_speed_point(speed_value)

    def close_receiving_popup(self, success, message):
        if self.receiving_popup:
            self.receiving_popup.dismiss()
            self.receiving_popup = None
        print(message)

    def build(self):
        Window.size = (400, 700)
        self.icon = resource_path('logo.svg')
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(DeviceDiscoveryScreen(screen_manager=sm, app=self, name='devices'))
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