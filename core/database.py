"""
MIT License

Copyright (c) 2019-2020 eibex

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import sqlite3
from random import randint


def initialize(database):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS 'messages' ('message_id' INT, 'channel' INT,"
        " 'reactionrole_id' INT);"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS 'reactionroles' ('reactionrole_id' INT, 'reaction'"
        " NVCARCHAR, 'role_id' INT);"
    )
    cursor.execute("CREATE TABLE IF NOT EXISTS 'admins' ('role_id' INT);")
    conn.commit()
    cursor.close()
    conn.close()


class ReactionRoleCreationTracker:
    def __init__(self, user, channel, database):
        self.database = database
        initialize(self.database)

        self.user = user
        self.channel = channel
        self.step = 0
        self.target_channel = None
        self.combos = {}
        self.message_id = None
        self._generate_reactionrole_id()

    def _generate_reactionrole_id(self):
        conn = sqlite3.connect(self.database)
        while True:
            self.reactionrole_id = randint(0, 100000)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM messages WHERE reactionrole_id = ?",
                (self.reactionrole_id,),
            )
            already_exists = cursor.fetchall()
            if already_exists:
                continue
            cursor.close()
            conn.close()
            break

    def commit(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO 'messages' ('message_id', 'channel', 'reactionrole_id')"
            " values(?, ?, ?);",
            (self.message_id, self.target_channel, self.reactionrole_id),
        )
        for reaction in self.combos:
            role_id = self.combos[reaction]
            cursor.execute(
                "INSERT INTO 'reactionroles' ('reactionrole_id', 'reaction', 'role_id')"
                " values(?, ?, ?);",
                (self.reactionrole_id, reaction, role_id),
            )
        conn.commit()
        cursor.close()
        conn.close()


class Database:
    def __init__(self, database):
        self.database = database
        initialize(self.database)

        self.reactionrole_creation = {}

    def start_creation(self, user, channel):
        tracker = ReactionRoleCreationTracker(user, channel, self.database)
        if not f"{user}_{channel}" in self.reactionrole_creation:
            self.reactionrole_creation[f"{user}_{channel}"] = tracker
            return True
        return False


    def abort(self, user, channel):
        if f"{user}_{channel}" in self.reactionrole_creation:
            del self.reactionrole_creation[f"{user}_{channel}"]
            return True
        return False


    def step(self, user, channel):
        if f"{user}_{channel}" in self.reactionrole_creation:
            tracker = self.reactionrole_creation[f"{user}_{channel}"]
            return tracker.step
        return None


    def get_targetchannel(self, user, channel):
        tracker = self.reactionrole_creation[f"{user}_{channel}"]
        return tracker.target_channel


    def get_combos(self, user, channel):
        tracker = self.reactionrole_creation[f"{user}_{channel}"]
        return tracker.combos


    def step0(self, user, channel):
        tracker = self.reactionrole_creation[f"{user}_{channel}"]
        tracker.step += 1


    def step1(self, user, channel, target_channel):
        tracker = self.reactionrole_creation[f"{user}_{channel}"]
        tracker.target_channel = target_channel
        tracker.step += 1


    def step2(self, user, channel, role=None, reaction=None, done=False):
        tracker = self.reactionrole_creation[f"{user}_{channel}"]
        if not done:
            tracker.combos[reaction] = role
        else:
            tracker.step += 1


    def end_creation(self, user, channel, message_id):
        tracker = self.reactionrole_creation[f"{user}_{channel}"]
        tracker.message_id = message_id
        try:
            tracker.commit()
        except sqlite3.Error as e:
            return e
        del self.reactionrole_creation[f"{user}_{channel}"]


    def exists(self, message_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages WHERE message_id = ?;", (message_id,))
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result
        except sqlite3.Error as e:
            return e


    def get_reactions(self, message_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reactionrole_id FROM messages WHERE message_id = ?;", (message_id,)
            )
            reactionrole_id = cursor.fetchall()[0][0]
            cursor.execute(
                "SELECT reaction, role_id FROM reactionroles WHERE reactionrole_id = ?;",
                (reactionrole_id,),
            )
            combos = {}
            for row in cursor:
                reaction = row[0]
                role_id = row[1]
                combos[reaction] = role_id
            cursor.close()
            conn.close()
            return combos
        except sqlite3.Error as e:
            return e


    def fetch_messages(self, channel):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute("SELECT message_id FROM messages WHERE channel = ?;", (channel,))
            all_messages_in_channel = []
            for row in cursor:
                message_id = int(row[0])
                all_messages_in_channel.append(message_id)
            cursor.close()
            conn.close()
            return all_messages_in_channel
        except sqlite3.Error as e:
            return e


    def fetch_all_messages(self):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(f"SELECT message_id, channel FROM messages;")
            all_messages = {}
            for row in cursor:
                message_id = int(row[0])
                channel_id = int(row[1])
                all_messages[message_id] = channel_id
            cursor.close()
            conn.close()
            return all_messages
        except sqlite3.Error as e:
            return e


    def delete(self, message_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reactionrole_id FROM messages WHERE message_id = ?;", (message_id,)
            )
            reactionrole_id = cursor.fetchall()[0][0]
            cursor.execute("DELETE FROM messages WHERE reactionrole_id = ?;", (reactionrole_id,))
            cursor.execute(
                "DELETE FROM reactionroles WHERE reactionrole_id = ?;", (reactionrole_id,)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            return e


    def add_admin(self, role):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO 'admins' ('role_id') values(?);", (role,))
            conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            return e


    def remove_admin(self, role):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM admins WHERE role_id = ?;", (role,))
            conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            return e


    def get_admins(self):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM admins;")
            admins = []
            for row in cursor:
                role_id = row[0]
                admins.append(role_id)
            cursor.close()
            conn.close()
            return admins
        except sqlite3.Error as e:
            return e
