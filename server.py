from flask import Flask, request, jsonify, render_template_string
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import sqlite3
from datetime import datetime
import threading
import hashlib
import json

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

db_lock = threading.Lock()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forevo</title>
    <style>
        :root {
            --bg: #1a1a2e; --sidebar: #16213e; --chat-bg: #1a1a2e; --input-bg: #0f3460;
            --msg-received: #0f3460; --msg-sent: #e94560; --text: #eee; --text-secondary: #666;
            --user-btn-bg: #0f3460; --user-btn-hover: #1a4a8a; --header-bg: #16213e;
        }
        .light-theme {
            --bg: #f0f2f5; --sidebar: #ffffff; --chat-bg: #f0f2f5; --input-bg: #e8e8e8;
            --msg-received: #ffffff; --msg-sent: #e94560; --text: #1a1a2e; --text-secondary: #888;
            --user-btn-bg: #f0f2f5; --user-btn-hover: #e0e0e0; --header-bg: #ffffff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); height: 100vh; display: flex; transition: all 0.3s; }
        
        .sidebar { width: 280px; background: var(--sidebar); padding: 20px; display: flex; flex-direction: column; transition: all 0.3s; }
        .sidebar h1 { margin-bottom: 5px; color: #e94560; font-size: 28px; }
        .sidebar .subtitle { margin-bottom: 15px; color: var(--text-secondary); font-size: 12px; }
        
        #auth-area { margin-bottom: 15px; }
        #auth-area input { width: 100%; padding: 10px; border: none; border-radius: 5px; background: var(--input-bg); color: var(--text); margin-bottom: 8px; }
        #auth-area button { width: 100%; padding: 10px; border: none; border-radius: 5px; background: #e94560; color: white; cursor: pointer; font-weight: bold; margin-bottom: 5px; }
        #auth-area button:hover { background: #c23152; }
        #auth-area .secondary { background: var(--input-bg); color: var(--text); }
        #auth-area .secondary:hover { background: var(--user-btn-hover); }
        .error { color: #ff6b6b; font-size: 12px; margin-bottom: 10px; }
        
        #user-info { display: none; margin-bottom: 15px; padding: 10px; background: var(--input-bg); border-radius: 8px; align-items: center; gap: 10px; }
        #user-info .user-avatar { font-size: 24px; }
        #user-info .user-name { flex: 1; font-weight: bold; }
        #user-info .settings-btn { background: none; border: none; color: var(--text); cursor: pointer; font-size: 18px; opacity: 0.7; }
        
        #users-list { flex: 1; overflow-y: auto; }
        .section-title { font-size: 11px; text-transform: uppercase; color: var(--text-secondary); padding: 10px 5px 5px; letter-spacing: 1px; }
        .user-btn { width: 100%; padding: 12px; margin-bottom: 5px; border: none; border-radius: 8px; background: var(--user-btn-bg); color: var(--text); cursor: pointer; text-align: left; font-size: 14px; display: flex; align-items: center; gap: 10px; }
        .user-btn:hover { background: var(--user-btn-hover); }
        .user-btn.active { background: #e94560; color: white; }
        .create-group-btn { width: 100%; padding: 10px; border: 2px dashed var(--text-secondary); border-radius: 8px; background: none; color: var(--text-secondary); cursor: pointer; font-size: 13px; margin-bottom: 10px; }
        .create-group-btn:hover { border-color: #e94560; color: #e94560; }
        .avatar { width: 35px; height: 35px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; background: rgba(255,255,255,0.15); }
        .online-dot { width: 8px; height: 8px; border-radius: 50%; margin-left: auto; flex-shrink: 0; }
        .online { background: #00ff88; } .offline { background: #666; }
        .group-meta { font-size: 10px; color: var(--text-secondary); }
        
        .chat-area { flex: 1; display: flex; flex-direction: column; background: var(--chat-bg); transition: all 0.3s; }
        .chat-header { padding: 20px; background: var(--header-bg); font-size: 18px; font-weight: bold; display: flex; align-items: center; gap: 10px; transition: all 0.3s; }
        .chat-header .members-count { font-size: 12px; opacity: 0.5; cursor: pointer; }
        .chat-header .members-count:hover { text-decoration: underline; }
        #messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
        
        .msg { max-width: 70%; padding: 8px 12px; border-radius: 12px; word-wrap: break-word; position: relative; }
        .msg.sent { align-self: flex-end; background: var(--msg-sent); color: white; border-bottom-right-radius: 4px; }
        .msg.received { align-self: flex-start; background: var(--msg-received); border-bottom-left-radius: 4px; }
        .light-theme .msg.received { box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .msg .sender { font-size: 11px; opacity: 0.7; margin-bottom: 2px; font-weight: bold; }
        .msg .reply-preview { font-size: 11px; opacity: 0.7; border-left: 3px solid rgba(255,255,255,0.5); padding-left: 8px; margin-bottom: 4px; cursor: pointer; }
        .msg .text { margin: 3px 0; }
        .msg .reactions { display: flex; gap: 3px; margin-top: 4px; flex-wrap: wrap; }
        .msg .reaction { background: rgba(255,255,255,0.15); padding: 2px 6px; border-radius: 10px; font-size: 14px; cursor: pointer; }
        .msg .reaction:hover { background: rgba(255,255,255,0.3); }
        .msg .time { font-size: 10px; opacity: 0.5; text-align: right; }
        .msg .actions { display: none; position: absolute; top: -8px; right: 5px; gap: 2px; background: var(--msg-sent); border-radius: 10px; padding: 2px; }
        .msg.sent:hover .actions { display: flex; }
        .msg.received .actions { background: var(--msg-received); }
        .msg.received:hover .actions { display: flex; }
        .msg .actions button { background: none; border: none; color: white; cursor: pointer; font-size: 12px; opacity: 0.8; padding: 3px 6px; border-radius: 8px; }
        .msg .actions button:hover { opacity: 1; background: rgba(255,255,255,0.2); }
        .msg .edited { font-size: 9px; opacity: 0.4; }
        
        .reply-bar { display: none; padding: 10px 20px; background: var(--header-bg); border-top: 1px solid var(--input-bg); align-items: center; gap: 10px; }
        .reply-bar .reply-text { flex: 1; font-size: 13px; opacity: 0.7; border-left: 3px solid #e94560; padding-left: 10px; }
        .reply-bar button { background: none; border: none; color: var(--text); cursor: pointer; font-size: 18px; }
        
        .input-area { padding: 15px 20px; background: var(--header-bg); display: flex; gap: 10px; transition: all 0.3s; }
        #message-input { flex: 1; padding: 12px; border: none; border-radius: 25px; background: var(--input-bg); color: var(--text); font-size: 14px; }
        #send-btn { padding: 12px 25px; border: none; border-radius: 25px; background: #e94560; color: white; cursor: pointer; font-weight: bold; }
        #send-btn:hover { background: #c23152; }
        #send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        #status { padding: 10px; text-align: center; font-size: 12px; color: var(--text-secondary); }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center; }
        .modal.show { display: flex; }
        .modal-content { background: var(--sidebar); padding: 30px; border-radius: 15px; max-width: 400px; width: 90%; max-height: 80vh; overflow-y: auto; }
        .modal-content h2 { margin-bottom: 20px; color: #e94560; }
        .modal-content h3 { margin: 15px 0 10px; font-size: 14px; color: var(--text-secondary); }
        .modal-content input { width: 100%; padding: 10px; border: none; border-radius: 5px; background: var(--input-bg); color: var(--text); margin-bottom: 10px; }
        .modal-content .setting-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid var(--input-bg); }
        .modal-content button { padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; margin-top: 5px; width: 100%; }
        .btn-danger { background: #e94560; color: white; }
        .btn-primary { background: var(--input-bg); color: var(--text); }
        .btn-small { width: auto !important; padding: 5px 10px !important; font-size: 12px !important; }
        .member-item { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 8px; }
        .member-item:hover { background: var(--input-bg); }
        .member-item .remove-btn { margin-left: auto; background: none; border: none; color: #e94560; cursor: pointer; font-size: 16px; }
        
        .emoji-picker { display: none; position: absolute; bottom: 80px; right: 20px; background: var(--sidebar); border-radius: 15px; padding: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.3); z-index: 100; }
        .emoji-picker.show { display: block; }
        .emoji-grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: 8px; }
        .emoji-item { font-size: 28px; cursor: pointer; padding: 5px; border-radius: 8px; text-align: center; }
        .emoji-item:hover { background: var(--input-bg); }
        
        .reaction-picker { display: none; position: fixed; background: var(--sidebar); border-radius: 20px; padding: 5px 10px; box-shadow: 0 3px 15px rgba(0,0,0,0.3); z-index: 200; gap: 5px; }
        .reaction-picker.show { display: flex; }
        .reaction-picker span { font-size: 20px; cursor: pointer; padding: 5px; border-radius: 10px; }
        .reaction-picker span:hover { background: var(--input-bg); }
        
        .switch { position: relative; display: inline-block; width: 50px; height: 26px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 26px; }
        .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: #e94560; }
        input:checked + .slider:before { transform: translateX(24px); }
        
        .leave-btn { background: none; border: none; color: #e94560; cursor: pointer; font-size: 13px; padding: 5px 10px; }
        .leave-btn:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h1>Forevo</h1>
        <div class="subtitle">вечное общение</div>
        
        <div id="auth-area">
            <input type="text" id="username-input" placeholder="Имя пользователя" maxlength="20">
            <input type="password" id="password-input" placeholder="Пароль" maxlength="30">
            <div class="error" id="auth-error"></div>
            <button onclick="register()">Регистрация</button>
            <button class="secondary" onclick="login()">Войти</button>
        </div>
        
        <div id="user-info">
            <span class="user-avatar" id="my-avatar"></span>
            <span class="user-name" id="my-name"></span>
            <button class="settings-btn" onclick="openSettings()">⚙️</button>
        </div>
        
        <div id="users-list"></div>
        <div id="status">Не подключен</div>
    </div>
    
    <div class="chat-area">
        <div class="chat-header" id="chat-header">👋 Добро пожаловать в Forevo</div>
        <div id="messages"></div>
        <div class="reply-bar" id="reply-bar">
            <span class="reply-text" id="reply-text"></span>
            <button onclick="cancelReply()">✕</button>
        </div>
        <div class="input-area">
            <input type="text" id="message-input" placeholder="Сообщение..." disabled>
            <button id="send-btn" onclick="sendMessage()" disabled>Отправить</button>
        </div>
        <div class="reaction-picker" id="reaction-picker">
            <span onclick="addReaction('👍')">👍</span><span onclick="addReaction('😂')">😂</span>
            <span onclick="addReaction('❤️')">❤️</span><span onclick="addReaction('🔥')">🔥</span>
            <span onclick="addReaction('💯')">💯</span><span onclick="addReaction('😢')">😢</span>
        </div>
    </div>
    
    <div class="modal" id="settings-modal">
        <div class="modal-content">
            <h2>⚙️ Настройки</h2>
            <div class="setting-row">
                <span>Тёмная тема</span>
                <label class="switch"><input type="checkbox" id="theme-toggle" onchange="toggleTheme()"><span class="slider"></span></label>
            </div>
            <div class="setting-row">
                <span>Аватар</span>
                <button class="btn-primary" style="width:auto;margin:0;" onclick="toggleEmojiPicker()">Выбрать эмодзи</button>
            </div>
            <div id="emoji-picker-container" style="position:relative;">
                <div class="emoji-picker" id="emoji-picker"><div class="emoji-grid" id="emoji-grid"></div></div>
            </div>
            <button class="btn-primary" onclick="logout()" style="margin-top:15px;">🚪 Выйти из аккаунта</button>
            <button class="btn-danger" onclick="deleteAccount()">🗑️ Удалить аккаунт</button>
            <button class="btn-primary" onclick="closeSettings()">Закрыть</button>
        </div>
    </div>
    
    <div class="modal" id="create-group-modal">
        <div class="modal-content">
            <h2>👥 Создать группу</h2>
            <input type="text" id="group-name-input" placeholder="Название группы">
            <h3>Добавить участников:</h3>
            <div id="add-members-list"></div>
            <button class="btn-primary" onclick="createGroup()">Создать</button>
            <button class="btn-primary" onclick="closeCreateGroup()">Отмена</button>
        </div>
    </div>
    
    <div class="modal" id="group-info-modal">
        <div class="modal-content">
            <h2 id="group-info-title">Информация о группе</h2>
            <div id="group-members-list"></div>
            <h3>Добавить участника:</h3>
            <div id="add-member-list"></div>
            <button class="btn-danger leave-btn" id="leave-group-btn" onclick="leaveGroup()">🚪 Покинуть группу</button>
            <button class="btn-primary" onclick="closeGroupInfo()">Закрыть</button>
        </div>
    </div>
    
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script>
        let socket = null, username = null, currentChat = null, currentChatType = 'user';
        let editingMsgId = null, replyingTo = null, userAvatar = '😊', reactionTarget = null;
        
        const emojis = ['😊','😂','❤️','😍','🤣','😁','😎','🥺','😡','😭','💀','👻','🎉','🔥','⭐','💖','🐱','🐶','🦊','🐸','🦄','🐼','🐨','🐯','🌺','🌸','🍕','🎸','🚀','🌈','💎','🍀'];
        
        if (localStorage.getItem('theme') === 'light') {
            document.body.classList.add('light-theme');
            document.getElementById('theme-toggle').checked = true;
        }
        
        function toggleTheme() {
            document.body.classList.toggle('light-theme');
            localStorage.setItem('theme', document.body.classList.contains('light-theme') ? 'light' : 'dark');
        }
        
        function playSound() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator(), gain = ctx.createGain();
                osc.connect(gain); gain.connect(ctx.destination);
                osc.frequency.value = 800; osc.type = 'sine'; gain.gain.value = 0.1;
                osc.start(); gain.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + 0.15);
                osc.stop(ctx.currentTime + 0.15);
            } catch(e) {}
        }
        
        function showError(msg) {
            document.getElementById('auth-error').textContent = msg;
            setTimeout(() => document.getElementById('auth-error').textContent = '', 3000);
        }
        
        function register() {
            const u = document.getElementById('username-input').value.trim();
            const p = document.getElementById('password-input').value.trim();
            if (!u || !p) { showError('Заполни все поля'); return; }
            if (p.length < 3) { showError('Пароль минимум 3 символа'); return; }
            fetch('/register', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})})
            .then(r=>r.json()).then(d=>{if(d.status==='ok'){username=u;connectSocket();}else showError(d.message||'Ошибка');});
        }
        
        function login() {
            const u = document.getElementById('username-input').value.trim();
            const p = document.getElementById('password-input').value.trim();
            if (!u || !p) { showError('Заполни все поля'); return; }
            fetch('/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})})
            .then(r=>r.json()).then(d=>{if(d.status==='ok'){username=u;connectSocket();}else showError(d.message||'Неверный логин или пароль');});
        }
        
        function connectSocket() {
           socket = io({transports: ['websocket'], upgrade: false});
            socket.on('connect', () => {
                document.getElementById('status').textContent = '✅ ' + username;
                document.getElementById('auth-area').style.display = 'none';
                document.getElementById('user-info').style.display = 'flex';
                document.getElementById('my-name').textContent = username;
                fetch(`/get_avatar/${username}`).then(r=>r.json()).then(d=>{
                    userAvatar=d.avatar||'😊';
                    document.getElementById('my-avatar').textContent=userAvatar;
                });
                socket.emit('login', {username: username});
            });
            socket.on('online_users', (users) => { loadSidebar(users); });
            socket.on('new_message', (data) => {
                playSound();
                if ((currentChatType==='group' && data.receiver===currentChat) || data.sender===currentChat || data.sender===username) {
                    addMessage(data);
                }
            });
            socket.on('message_deleted', (data) => {
                const el = document.getElementById('msg-'+data.id); if(el)el.remove();
            });
            socket.on('message_edited', (data) => {
                const el = document.getElementById('msg-'+data.id);
                if(el){el.querySelector('.text').textContent=data.message;if(!el.querySelector('.edited')){const e=document.createElement('span');e.className='edited';e.textContent='(изм.)';el.querySelector('.time').before(e);}}
            });
            socket.on('reaction_added', (data) => { updateReactions(data.id, data.reactions); });
            socket.on('group_created', () => { loadSidebar([]); });
            socket.on('group_updated', () => { loadSidebar([]); });
            socket.on('avatar_updated', () => { loadSidebar([]); });
            socket.on('disconnect', () => { document.getElementById('status').textContent='❌ Отключен'; });
        }
        
        function loadSidebar(onlineUsers) {
            Promise.all([fetch('/users').then(r=>r.json()), fetch('/my_groups/'+username).then(r=>r.json())])
            .then(([usersData, groupsData]) => {
                const container = document.getElementById('users-list');
                container.innerHTML = '';
                
                // Кнопка создать группу
                const createBtn = document.createElement('button');
                createBtn.className = 'create-group-btn';
                createBtn.textContent = '+ Создать группу';
                createBtn.onclick = openCreateGroup;
                container.appendChild(createBtn);
                
                // Группы
                if (groupsData.groups.length > 0) {
                    const title = document.createElement('div');
                    title.className = 'section-title'; title.textContent = 'Группы';
                    container.appendChild(title);
                    
                    groupsData.groups.forEach(g => {
                        const btn = document.createElement('button');
                        btn.className = 'user-btn';
                        btn.innerHTML = `<div class="avatar">👥</div><span>${g.name}</span><span class="group-meta">${g.members_count} уч.</span>`;
                        btn.onclick = () => openGroupChat(g.id, g.name);
                        if (currentChat === g.id && currentChatType === 'group') btn.classList.add('active');
                        container.appendChild(btn);
                    });
                }
                
                // Пользователи
                const title = document.createElement('div');
                title.className = 'section-title'; title.textContent = 'Личные чаты';
                container.appendChild(title);
                
                usersData.users.forEach(user => {
                    if (user[0] !== username) {
                        const isOnline = onlineUsers.includes(user[0]);
                        const btn = document.createElement('button');
                        btn.className = 'user-btn';
                        btn.innerHTML = `<div class="avatar">${user[1]||'😊'}</div><span>${user[0]}</span><span class="online-dot ${isOnline?'online':'offline'}"></span>`;
                        btn.onclick = () => openChat(user[0]);
                        if (user[0] === currentChat && currentChatType === 'user') btn.classList.add('active');
                        container.appendChild(btn);
                    }
                });
            });
        }
        
        function openChat(user) {
            currentChat = user; currentChatType = 'user';
            document.getElementById('chat-header').innerHTML = `💬 Чат с ${user}`;
            document.getElementById('message-input').disabled = false;
            document.getElementById('send-btn').disabled = false;
            document.getElementById('messages').innerHTML = '';
            cancelReply();
            fetch(`/messages/${username}/${user}`).then(r=>r.json()).then(d=>d.messages.forEach(m=>addMessage(m)));
        }
        
        function openGroupChat(groupId, groupName) {
            currentChat = groupId; currentChatType = 'group';
            document.getElementById('chat-header').innerHTML = `👥 ${groupName} <span class="members-count" onclick="openGroupInfo('${groupId}')">(инфо)</span>`;
            document.getElementById('message-input').disabled = false;
            document.getElementById('send-btn').disabled = false;
            document.getElementById('messages').innerHTML = '';
            cancelReply();
            fetch(`/group_messages/${groupId}`).then(r=>r.json()).then(d=>d.messages.forEach(m=>addMessage(m)));
        }
        
        function addMessage(msg) {
            const div = document.createElement('div');
            div.className = 'msg ' + (msg.sender === username ? 'sent' : 'received');
            div.id = 'msg-' + msg.id;
            
            let replyHtml = msg.reply_to ? `<div class="reply-preview" onclick="scrollToMsg(${msg.reply_to.id})">↩ ${msg.reply_to.sender}: ${msg.reply_to.text.substring(0,50)}</div>` : '';
            
            let reactionsHtml = '';
            if (msg.reactions && Object.keys(msg.reactions).length > 0) {
                reactionsHtml = '<div class="reactions">';
                for (const [emoji, count] of Object.entries(msg.reactions)) {
                    reactionsHtml += `<span class="reaction" onclick="quickReact(${msg.id},'${emoji}')">${emoji} ${count}</span>`;
                }
                reactionsHtml += '</div>';
            }
            
            let actionsHtml = `<div class="actions">
                <button onclick="showReactionPicker(event,${msg.id})">😀</button>
                <button onclick="replyTo(${msg.id},'${msg.sender}','${msg.message.replace(/'/g,"\\'").substring(0,50)}')">↩</button>
                ${msg.sender===username?`<button onclick="editMsg(${msg.id},'${msg.message.replace(/'/g,"\\'")}')">✏️</button><button onclick="deleteMsg(${msg.id})">🗑️</button>`:''}
            </div>`;
            
            div.innerHTML = `${actionsHtml}<div class="sender">${msg.sender===username?'Ты':msg.sender}</div>${replyHtml}<div class="text">${msg.message}</div>${reactionsHtml}<div class="time">${msg.timestamp||''} ${msg.edited?'<span class="edited">(изм.)</span>':''}</div>`;
            document.getElementById('messages').appendChild(div);
            document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
        }
        
        function updateReactions(msgId, reactions) {
            const el = document.getElementById('msg-'+msgId); if(!el)return;
            let reactionsDiv = el.querySelector('.reactions');
            if(!reactionsDiv){reactionsDiv=document.createElement('div');reactionsDiv.className='reactions';el.querySelector('.time').before(reactionsDiv);}
            reactionsDiv.innerHTML='';
            if(reactions && Object.keys(reactions).length>0){
                for(const[emoji,count] of Object.entries(reactions)){
                    const span=document.createElement('span');span.className='reaction';span.textContent=`${emoji} ${count}`;span.onclick=()=>quickReact(msgId,emoji);reactionsDiv.appendChild(span);
                }
            }
        }
        
        function showReactionPicker(e, msgId) {
            e.stopPropagation(); reactionTarget = msgId;
            const picker = document.getElementById('reaction-picker');
            picker.style.top = (e.clientY - 50) + 'px';
            picker.style.left = (e.clientX - 80) + 'px';
            picker.classList.add('show');
            setTimeout(() => document.addEventListener('click', hideReactionPicker), 100);
        }
        
        function hideReactionPicker() {
            document.getElementById('reaction-picker').classList.remove('show');
            document.removeEventListener('click', hideReactionPicker);
        }
        
        function addReaction(emoji) {
            if(reactionTarget){socket.emit('add_reaction',{message_id:reactionTarget,emoji:emoji,username:username});hideReactionPicker();}
        }
        
        function quickReact(msgId, emoji) { socket.emit('add_reaction',{message_id:msgId,emoji:emoji,username:username}); }
        
        function replyTo(msgId, sender, text) {
            replyingTo = {id:msgId, sender:sender, text:text};
            document.getElementById('reply-text').textContent = `${sender}: ${text}`;
            document.getElementById('reply-bar').style.display = 'flex';
            document.getElementById('message-input').focus();
        }
        
        function cancelReply() { replyingTo=null; document.getElementById('reply-bar').style.display='none'; }
        function scrollToMsg(id) { const el=document.getElementById('msg-'+id); if(el)el.scrollIntoView({behavior:'smooth',block:'center'}); }
        
        function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            if(!message||!currentChat)return;
            
            if(editingMsgId){
                socket.emit('edit_message',{id:editingMsgId,message:message});
                editingMsgId=null;document.getElementById('send-btn').textContent='Отправить';
            }else{
                socket.emit('send_message',{
                    sender:username,
                    receiver:currentChatType==='group'?currentChat:currentChat,
                    message:message,
                    reply_to:replyingTo,
                    is_group:currentChatType==='group'
                });
                cancelReply();
            }
            input.value='';
        }
        
        function editMsg(id, text) {
            editingMsgId=id;
            document.getElementById('message-input').value=text;
            document.getElementById('send-btn').textContent='Сохранить';
            document.getElementById('message-input').focus();
        }
        
        function deleteMsg(id) { if(confirm('Удалить сообщение?'))socket.emit('delete_message',{id:id}); }
        
        // Группы
        function openCreateGroup() {
            document.getElementById('create-group-modal').classList.add('show');
            document.getElementById('group-name-input').value = '';
            fetch('/users').then(r=>r.json()).then(d=>{
                const list = document.getElementById('add-members-list');
                list.innerHTML = '';
                d.users.forEach(user => {
                    if(user[0]!==username){
                        const div = document.createElement('div');
                        div.className = 'setting-row';
                        div.innerHTML = `<span>${user[0]}</span><label class="switch"><input type="checkbox" class="member-check" value="${user[0]}"><span class="slider"></span></label>`;
                        list.appendChild(div);
                    }
                });
            });
        }
        
        function closeCreateGroup() { document.getElementById('create-group-modal').classList.remove('show'); }
        
        function createGroup() {
            const name = document.getElementById('group-name-input').value.trim();
            if(!name){alert('Введите название');return;}
            const members = [];
            document.querySelectorAll('.member-check:checked').forEach(cb => members.push(cb.value));
            if(members.length===0){alert('Выберите хотя бы одного участника');return;}
            
            fetch('/create_group',{
                method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({name:name,creator:username,members:members})
            }).then(r=>r.json()).then(d=>{
                if(d.status==='ok'){
                    closeCreateGroup();
                    socket.emit('group_created',{});
                }
            });
        }
        
        function openGroupInfo(groupId) {
            document.getElementById('group-info-modal').classList.add('show');
            document.getElementById('group-info-title').textContent = 'Информация о группе';
            
            fetch(`/group_info/${groupId}`).then(r=>r.json()).then(d=>{
                const membersList = document.getElementById('group-members-list');
                membersList.innerHTML = '<h3>Участники:</h3>';
                d.members.forEach(m => {
                    const div = document.createElement('div');
                    div.className = 'member-item';
                    div.innerHTML = `<span>${m}</span>${d.creator===username&&m!==username?`<button class="remove-btn" onclick="removeMember('${groupId}','${m}')">✕</button>`:''}`;
                    membersList.appendChild(div);
                });
                
                // Список для добавления
                const addList = document.getElementById('add-member-list');
                addList.innerHTML = '';
                fetch('/users').then(r=>r.json()).then(ud=>{
                    ud.users.forEach(u => {
                        if(u[0]!==username && !d.members.includes(u[0])){
                            const btn = document.createElement('button');
                            btn.className = 'btn-primary btn-small';
                            btn.style.cssText = 'width:auto;display:inline-block;margin:3px;';
                            btn.textContent = '+ '+u[0];
                            btn.onclick = () => addMember(groupId, u[0]);
                            addList.appendChild(btn);
                        }
                    });
                });
                
                document.getElementById('leave-group-btn').style.display = 'block';
            });
        }
        
        function closeGroupInfo() { document.getElementById('group-info-modal').classList.remove('show'); }
        
        function addMember(groupId, member) {
            fetch('/add_member',{
                method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({group_id:groupId,username:member})
            }).then(()=>{openGroupInfo(groupId);socket.emit('group_updated',{});});
        }
        
        function removeMember(groupId, member) {
            fetch('/remove_member',{
                method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({group_id:groupId,username:member})
            }).then(()=>{openGroupInfo(groupId);socket.emit('group_updated',{});});
        }
        
        function leaveGroup() {
            if(!confirm('Покинуть группу?'))return;
            fetch('/leave_group',{
                method:'POST',headers:{'Content-Type':'application/json'},
                body:JSON.stringify({group_id:currentChat,username:username})
            }).then(()=>{
                closeGroupInfo();
                currentChat=null;
                document.getElementById('chat-header').textContent='👋 Добро пожаловать в Forevo';
                document.getElementById('messages').innerHTML='';
                socket.emit('group_updated',{});
            });
        }
        
        // Настройки
        function openSettings() { document.getElementById('settings-modal').classList.add('show'); initEmojiPicker(); }
        function closeSettings() { document.getElementById('settings-modal').classList.remove('show'); document.getElementById('emoji-picker').classList.remove('show'); }
        function initEmojiPicker() {
            const grid=document.getElementById('emoji-grid');grid.innerHTML='';
            emojis.forEach(e=>{const d=document.createElement('div');d.className='emoji-item';d.textContent=e;d.onclick=()=>selectAvatar(e);grid.appendChild(d);});
        }
        function toggleEmojiPicker(){document.getElementById('emoji-picker').classList.toggle('show');}
        function selectAvatar(emoji){
            userAvatar=emoji;document.getElementById('my-avatar').textContent=emoji;document.getElementById('emoji-picker').classList.remove('show');
            fetch('/set_avatar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:username,avatar:emoji})}).then(()=>{socket.emit('avatar_changed',{username:username});});
        }
        function logout(){
            if(socket)socket.disconnect();
            username=null;currentChat=null;currentChatType='user';
            document.getElementById('auth-area').style.display='block';
            document.getElementById('user-info').style.display='none';
            document.getElementById('chat-header').textContent='👋 Добро пожаловать в Forevo';
            document.getElementById('messages').innerHTML='';
            document.getElementById('message-input').disabled=true;
            document.getElementById('send-btn').disabled=true;
            document.getElementById('status').textContent='Не подключен';
            cancelReply();closeSettings();
        }
        function deleteAccount(){
            if(!confirm('Точно удалить аккаунт?'))return;
            fetch('/delete_account',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:username})}).then(()=>logout());
        }
        
        document.getElementById('message-input').addEventListener('keypress',(e)=>{if(e.key==='Enter')sendMessage();});
        document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',function(e){if(e.target===this){this.classList.remove('show');document.getElementById('emoji-picker').classList.remove('show');}}));
        document.addEventListener('click',(e)=>{if(!e.target.closest('.reaction-picker')&&!e.target.closest('.actions button'))hideReactionPicker();});
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def init_db():
    conn = sqlite3.connect('messenger.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  avatar TEXT DEFAULT '😊')''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  receiver TEXT NOT NULL,
                  message TEXT NOT NULL,
                  reply_to TEXT,
                  reactions TEXT DEFAULT '{}',
                  edited INTEGER DEFAULT 0,
                  deleted INTEGER DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS groups_chat
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  creator TEXT NOT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS group_members
                 (group_id INTEGER NOT NULL,
                  username TEXT NOT NULL,
                  PRIMARY KEY (group_id, username))''')
    try: c.execute('ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT "😊"')
    except: pass
    try: c.execute('ALTER TABLE messages ADD COLUMN reply_to TEXT')
    except: pass
    try: c.execute('ALTER TABLE messages ADD COLUMN reactions TEXT DEFAULT "{}"')
    except: pass
    conn.commit()
    conn.close()

init_db()

online_users = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if len(username) < 2: return jsonify({'status': 'error', 'message': 'Имя слишком короткое'})
    if len(password) < 3: return jsonify({'status': 'error', 'message': 'Пароль минимум 3 символа'})
    try:
        with db_lock:
            conn = sqlite3.connect('messenger.db'); c = conn.cursor()
            c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hash_password(password)))
            conn.commit(); conn.close()
        return jsonify({'status': 'ok'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Пользователь уже существует'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('SELECT password_hash FROM users WHERE username=?', (username,))
        row = c.fetchone(); conn.close()
    if row and row[0] == hash_password(password): return jsonify({'status': 'ok'})
    return jsonify({'status': 'error', 'message': 'Неверный логин или пароль'})

@app.route('/users', methods=['GET'])
def get_users():
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('SELECT username, avatar FROM users')
        users = [(row[0], row[1]) for row in c.fetchall()]; conn.close()
    return jsonify({'users': users})

@app.route('/get_avatar/<username>', methods=['GET'])
def get_avatar(username):
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('SELECT avatar FROM users WHERE username=?', (username,))
        row = c.fetchone(); conn.close()
    return jsonify({'avatar': row[0] if row else '😊'})

@app.route('/set_avatar', methods=['POST'])
def set_avatar():
    data = request.json
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('UPDATE users SET avatar=? WHERE username=?', (data['avatar'], data['username']))
        conn.commit(); conn.close()
    return jsonify({'status': 'ok'})

@app.route('/delete_account', methods=['POST'])
def delete_account():
    data = request.json
    username = data['username']
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('DELETE FROM messages WHERE sender=? OR receiver=?', (username, username))
        c.execute('DELETE FROM group_members WHERE username=?', (username,))
        c.execute('DELETE FROM groups_chat WHERE creator=?', (username,))
        c.execute('DELETE FROM users WHERE username=?', (username,))
        conn.commit(); conn.close()
    if username in online_users: del online_users[username]
    emit('online_users', list(online_users.keys()), broadcast=True)
    return jsonify({'status': 'ok'})

@app.route('/create_group', methods=['POST'])
def create_group():
    data = request.json
    name = data['name']
    creator = data['creator']
    members = data['members']
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('INSERT INTO groups_chat (name, creator) VALUES (?, ?)', (name, creator))
        group_id = c.lastrowid
        c.execute('INSERT INTO group_members (group_id, username) VALUES (?, ?)', (group_id, creator))
        for m in members:
            c.execute('INSERT OR IGNORE INTO group_members (group_id, username) VALUES (?, ?)', (group_id, m))
        conn.commit(); conn.close()
    return jsonify({'status': 'ok', 'group_id': group_id})

@app.route('/my_groups/<username>', methods=['GET'])
def my_groups(username):
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('''SELECT g.id, g.name, (SELECT COUNT(*) FROM group_members WHERE group_id=g.id) as cnt
                     FROM groups_chat g JOIN group_members gm ON g.id=gm.group_id
                     WHERE gm.username=?''', (username,))
        groups = [{'id': row[0], 'name': row[1], 'members_count': row[2]} for row in c.fetchall()]
        conn.close()
    return jsonify({'groups': groups})

@app.route('/group_info/<int:group_id>', methods=['GET'])
def group_info(group_id):
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('SELECT name, creator FROM groups_chat WHERE id=?', (group_id,))
        group = c.fetchone()
        c.execute('SELECT username FROM group_members WHERE group_id=?', (group_id,))
        members = [row[0] for row in c.fetchall()]
        conn.close()
    return jsonify({'name': group[0], 'creator': group[1], 'members': members})

@app.route('/add_member', methods=['POST'])
def add_member():
    data = request.json
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO group_members (group_id, username) VALUES (?, ?)',
                  (data['group_id'], data['username']))
        conn.commit(); conn.close()
    return jsonify({'status': 'ok'})

@app.route('/remove_member', methods=['POST'])
def remove_member():
    data = request.json
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('DELETE FROM group_members WHERE group_id=? AND username=?',
                  (data['group_id'], data['username']))
        conn.commit(); conn.close()
    return jsonify({'status': 'ok'})

@app.route('/leave_group', methods=['POST'])
def leave_group():
    data = request.json
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('DELETE FROM group_members WHERE group_id=? AND username=?',
                  (data['group_id'], data['username']))
        # Если создатель вышел — удаляем группу
        c.execute('SELECT creator FROM groups_chat WHERE id=?', (data['group_id'],))
        row = c.fetchone()
        if row and row[0] == data['username']:
            c.execute('DELETE FROM group_members WHERE group_id=?', (data['group_id'],))
            c.execute('DELETE FROM messages WHERE receiver=?', (str(data['group_id']),))
            c.execute('DELETE FROM groups_chat WHERE id=?', (data['group_id'],))
        conn.commit(); conn.close()
    return jsonify({'status': 'ok'})

@app.route('/messages/<user1>/<user2>', methods=['GET'])
def get_messages(user1, user2):
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('''SELECT id, sender, receiver, message, reply_to, reactions, edited, timestamp 
                     FROM messages WHERE deleted=0 AND receiver NOT LIKE 'g_%' AND
                     ((sender=? AND receiver=?) OR (sender=? AND receiver=?))
                     ORDER BY timestamp''', (user1, user2, user2, user1))
        msgs = [{'id':r[0],'sender':r[1],'receiver':r[2],'message':r[3],'reply_to':json.loads(r[4])if r[4]else None,'reactions':json.loads(r[5])if r[5]else{},'edited':r[6],'timestamp':r[7]} for r in c.fetchall()]
        conn.close()
    return jsonify({'messages': msgs})

@app.route('/group_messages/<int:group_id>', methods=['GET'])
def get_group_messages(group_id):
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('''SELECT id, sender, receiver, message, reply_to, reactions, edited, timestamp 
                     FROM messages WHERE deleted=0 AND receiver=?
                     ORDER BY timestamp''', (str(group_id),))
        msgs = [{'id':r[0],'sender':r[1],'receiver':r[2],'message':r[3],'reply_to':json.loads(r[4])if r[4]else None,'reactions':json.loads(r[5])if r[5]else{},'edited':r[6],'timestamp':r[7]} for r in c.fetchall()]
        conn.close()
    return jsonify({'messages': msgs})

@socketio.on('login')
def handle_login(data):
    username = data['username']
    online_users[username] = request.sid
    join_room(username)
    # Вступаем во все группы пользователя
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('SELECT group_id FROM group_members WHERE username=?', (username,))
        for row in c.fetchall():
            join_room(str(row[0]))
        conn.close()
    emit('online_users', list(online_users.keys()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    for username, sid in list(online_users.items()):
        if sid == request.sid:
            del online_users[username]
            emit('online_users', list(online_users.keys()), broadcast=True)
            break

@socketio.on('send_message')
def handle_message(data):
    sender = data['sender']
    receiver = data['receiver']
    message = data['message']
    reply_to = json.dumps(data.get('reply_to')) if data.get('reply_to') else None
    timestamp = datetime.now().strftime('%H:%M')
    
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('INSERT INTO messages (sender, receiver, message, reply_to) VALUES (?,?,?,?)',
                  (sender, receiver, message, reply_to))
        msg_id = c.lastrowid; conn.commit(); conn.close()
    
    msg_data = {'id':msg_id,'sender':sender,'receiver':receiver,'message':message,'reply_to':data.get('reply_to'),'reactions':{},'edited':0,'timestamp':timestamp}
    
    emit('new_message', msg_data, room=sender)
    if not data.get('is_group'):
        emit('new_message', msg_data, room=receiver)

@socketio.on('delete_message')
def handle_delete(data):
    msg_id = data['id']
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('UPDATE messages SET deleted=1 WHERE id=?', (msg_id,)); conn.commit()
        c.execute('SELECT sender, receiver FROM messages WHERE id=?', (msg_id,))
        row = c.fetchone(); conn.close()
    if row:
        emit('message_deleted', {'id': msg_id}, room=row[0])
        if not row[1].startswith('g_'): emit('message_deleted', {'id': msg_id}, room=row[1])

@socketio.on('edit_message')
def handle_edit(data):
    msg_id, new_message = data['id'], data['message']
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('UPDATE messages SET message=?, edited=1 WHERE id=?', (new_message, msg_id)); conn.commit()
        c.execute('SELECT sender, receiver FROM messages WHERE id=?', (msg_id,))
        row = c.fetchone(); conn.close()
    if row:
        emit('message_edited', {'id':msg_id,'message':new_message}, room=row[0])
        if not row[1].startswith('g_'): emit('message_edited', {'id':msg_id,'message':new_message}, room=row[1])

@socketio.on('add_reaction')
def handle_reaction(data):
    msg_id, emoji, username = data['message_id'], data['emoji'], data['username']
    with db_lock:
        conn = sqlite3.connect('messenger.db'); c = conn.cursor()
        c.execute('SELECT reactions FROM messages WHERE id=?', (msg_id,))
        row = c.fetchone()
        if row:
            reactions = json.loads(row[0]) if row[0] else {}
            reactions[emoji] = reactions.get(emoji, 0) + 1
            c.execute('UPDATE messages SET reactions=? WHERE id=?', (json.dumps(reactions), msg_id)); conn.commit()
            c.execute('SELECT sender, receiver FROM messages WHERE id=?', (msg_id,))
            room_row = c.fetchone()
        conn.close()
    if room_row:
        update_data = {'id':msg_id,'reactions':reactions}
        emit('reaction_added', update_data, room=room_row[0])
        if not room_row[1].startswith('g_'): emit('reaction_added', update_data, room=room_row[1])

@socketio.on('group_created')
def handle_group_created(data):
    emit('group_created', {}, broadcast=True)

@socketio.on('group_updated')
def handle_group_updated(data):
    emit('group_updated', {}, broadcast=True)

@socketio.on('avatar_changed')
def handle_avatar(data):
    emit('avatar_updated', data, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
