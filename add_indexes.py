import os
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

conn = psycopg2.connect(DATABASE_URL)
c = conn.cursor()

# Создаём индексы
print("Создаю индексы...")

c.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)')
c.execute('CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver)')
c.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
c.execute('CREATE INDEX IF NOT EXISTS idx_group_members_username ON group_members(username)')
c.execute('CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id)')

conn.commit()
conn.close()

print("Индексы успешно созданы!")
