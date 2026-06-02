import customtkinter as ctk
import requests
import socketio
import threading

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Адрес сервера (поменяй на свой при деплое)
SERVER_URL = "http://localhost:5000"

class MessengerApp:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("Мессенджер")
        self.window.geometry("800x600")
        
        self.username = None
        self.current_chat = None
        self.sio = socketio.Client()
        self.setup_socket()
        
        # Страница логина
        self.show_login()
    
    def setup_socket(self):
        @self.sio.on('online_users')
        def on_online_users(users):
            self.window.after(0, lambda: self.update_users_list(users))
        
        @self.sio.on('new_message')
        def on_new_message(data):
            self.window.after(0, lambda: self.receive_message(data))
    
    def connect_socket(self):
        try:
            self.sio.connect(SERVER_URL)
            self.sio.emit('login', {'username': self.username})
        except:
            print("Не удалось подключиться к серверу")
    
    def show_login(self):
        self.clear_window()
        
        frame = ctk.CTkFrame(self.window)
        frame.pack(expand=True)
        
        ctk.CTkLabel(frame, text="Введите имя:", font=("Arial", 20)).pack(pady=10)
        self.login_entry = ctk.CTkEntry(frame, width=250, font=("Arial", 16))
        self.login_entry.pack(pady=10)
        
        ctk.CTkButton(frame, text="Войти", command=self.login, width=200).pack(pady=10)
        
        self.login_status = ctk.CTkLabel(frame, text="")
        self.login_status.pack(pady=5)
    
    def login(self):
        username = self.login_entry.get().strip()
        if not username:
            self.login_status.configure(text="Введите имя!", text_color="red")
            return
        
        # Регистрируем (если есть - норм)
        try:
            requests.post(f"{SERVER_URL}/register", json={"username": username})
        except:
            self.login_status.configure(text="Сервер недоступен!", text_color="red")
            return
        
        self.username = username
        self.connect_socket()
        self.show_main()
    
    def show_main(self):
        self.clear_window()
        
        # Левая панель - список пользователей
        left_frame = ctk.CTkFrame(self.window, width=250)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        ctk.CTkLabel(left_frame, text="Пользователи", font=("Arial", 18, "bold")).pack(pady=10)
        
        self.users_list = ctk.CTkScrollableFrame(left_frame)
        self.users_list.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Правая панель - чат
        right_frame = ctk.CTkFrame(self.window)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        self.chat_header = ctk.CTkLabel(right_frame, text="Выберите собеседника", font=("Arial", 16, "bold"))
        self.chat_header.pack(pady=10)
        
        self.messages_frame = ctk.CTkScrollableFrame(right_frame)
        self.messages_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Поле ввода
        input_frame = ctk.CTkFrame(right_frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        self.message_entry = ctk.CTkEntry(input_frame, font=("Arial", 14))
        self.message_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkButton(input_frame, text="Отправить", command=self.send_message, width=100).pack(side="right", padx=5)
        
        # Привязываем Enter
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        
        # Загружаем пользователей
        self.load_users()
    
    def load_users(self):
        try:
            response = requests.get(f"{SERVER_URL}/users")
            users = response.json()['users']
            for user in users:
                if user != self.username:
                    self.add_user_button(user)
        except:
            pass
    
    def update_users_list(self, online_users):
        # Очищаем и обновляем
        for widget in self.users_list.winfo_children():
            widget.destroy()
        
        try:
            all_users = requests.get(f"{SERVER_URL}/users").json()['users']
            for user in all_users:
                if user != self.username:
                    online = user in online_users
                    self.add_user_button(user, online)
        except:
            pass
    
    def add_user_button(self, username, online=False):
        status = "🟢" if online else "⚫"
        btn = ctk.CTkButton(
            self.users_list, 
            text=f"{status} {username}", 
            command=lambda u=username: self.open_chat(u),
            anchor="w"
        )
        btn.pack(fill="x", padx=5, pady=2)
    
    def open_chat(self, username):
        self.current_chat = username
        self.chat_header.configure(text=f"Чат с {username}")
        
        # Очищаем сообщения
        for widget in self.messages_frame.winfo_children():
            widget.destroy()
        
        # Загружаем историю
        try:
            response = requests.get(f"{SERVER_URL}/messages/{self.username}/{username}")
            messages = response.json()['messages']
            for msg in messages:
                self.display_message(msg)
        except:
            pass
    
    def display_message(self, msg):
        is_me = msg['sender'] == self.username
        align = "e" if is_me else "w"
        color = "#1a73e8" if is_me else "#333333"
        
        frame = ctk.CTkFrame(self.messages_frame, fg_color=color)
        frame.pack(anchor=align, padx=10, pady=5, fill="x")
        
        text = f"{msg['sender']}: {msg['message']}"
        lbl = ctk.CTkLabel(frame, text=text, wraplength=300, justify="left")
        lbl.pack(padx=10, pady=5)
    
    def send_message(self):
        if not self.current_chat:
            return
        
        message = self.message_entry.get().strip()
        if not message:
            return
        
        self.sio.emit('send_message', {
            'sender': self.username,
            'receiver': self.current_chat,
            'message': message
        })
        
        self.message_entry.delete(0, "end")
    
    def receive_message(self, data):
        if data['sender'] == self.current_chat:
            self.display_message(data)
    
    def clear_window(self):
        for widget in self.window.winfo_children():
            widget.destroy()
    
    def run(self):
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()
    
    def on_close(self):
        try:
            self.sio.disconnect()
        except:
            pass
        self.window.destroy()

if __name__ == "__main__":
    app = MessengerApp()
    app.run()