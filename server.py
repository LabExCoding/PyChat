import asynchat
import asyncore


# define the port
PORT = 6666

# define end exception class
class EndSession(Exception):
    pass


class ChatServer(asyncore.dispatcher):
    """
    Chat server
    """

    def __init__(self, port):
        asyncore.dispatcher.__init__(self)
        # create socket
        self.create_socket()
        # set socket into recyclable
        self.set_reuse_addr()
        # listen port
        self.bind(('', port))
        self.listen(5)
        self.users = {}
        self.main_room = ChatRoom(self)

    def handle_accept(self):
        conn, addr = self.accept()
        ChatSession(self, conn)

class ChatSession(asynchat.async_chat):
    """
    Responsible for communication with clients
    """

    def __init__(self, server, sock):
        asynchat.async_chat.__init__(self, sock)
        self.server = server
        self.set_terminator(b'\n')
        self.data = []
        self.name = None
        self.enter(LoginRoom(server))

    def enter(self, room):
        # Remove yourself from the current room and add it to the designated room
        try:
            cur = self.room
        except AttributeError:
            pass
        else:
            cur.remove(self)
        self.room = room
        room.add(self)

    def collect_incoming_data(self, data):
        # receive data from client
        self.data.append(data.decode("utf-8"))

    def found_terminator(self):
        # when a piece of data at the end of the client
        line = ''.join(self.data)
        self.data = []
        try:
            self.room.handle(self, line.encode("utf-8"))
        # when you exit the chat room
        except EndSession:
            self.handle_close()

    def handle_close(self):
        # when session is off?you'll enter LogoutRoom
        asynchat.async_chat.handle_close(self)
        self.enter(LogoutRoom(self.server))

class CommandHandler:
    """
    command processing class
    """

    def unknown(self, session, cmd):
        # Respond to unknown command
        # send messages via aynchat.async_chat.push method
        session.push(('Unknown command {} \n'.format(cmd)).encode("utf-8"))

    def handle(self, session, line):
        line = line.decode()
        # command process
        if not line.strip():
            return
        parts = line.split(' ', 1)
        cmd = parts[0]
        try:
            line = parts[1].strip()
        except IndexError:
            line = ''
        # Execute the corresponding method through the protocol code
        method = getattr(self, 'do_' + cmd, None)
        try:
            method(session, line)
        except TypeError:
            self.unknown(session, cmd)

class Room(CommandHandler):
    """
    Environment with multiple users, responsible for basic command processing and broadcasting
    """

    def __init__(self, server):
        self.server = server
        self.sessions = []

    def add(self, session):
        # a user enters the room
        self.sessions.append(session)

    def remove(self, session):
        # a user leaves the room
        self.sessions.remove(session)

    def broadcast(self, line):
        # Send specified messages to all users
        # send data using asynchat.asyn_chat.push method
        for session in self.sessions:
            session.push(line)

    def do_logout(self, session, line):
        # exit the room
        raise EndSession


class LoginRoom(Room):
    """
    Handle login users
    """

    def add(self, session):
        # User connection successful response
        Room.add(self, session)
        # Send data using asynchat.asyn_chat.push method
        session.push(b'Connect Success')

    def do_login(self, session, line):
        # User login logic
        name = line.strip()
        # Obtain user name
        if not name:
            session.push(b'UserName Empty')
        # Check for a user with the same name
        elif name in self.server.users:
            session.push(b'UserName Exist')
        # After successful user name check, enter the main chat room
        else:
            session.name = name
            session.enter(self.server.main_room)


class LogoutRoom(Room):
    """
    handle exit user
    """

    def add(self, session):
        # remove from server
        try:
            del self.server.users[session.name]
        except KeyError:
            pass


class ChatRoom(Room):
    """
    chatting room
    """

    def add(self, session):
        # broadcast when a new user enters
        session.push(b'Login Success')
        self.broadcast((session.name + ' has entered the room.\n').encode("utf-8"))
        self.server.users[session.name] = session
        Room.add(self, session)

    def remove(self, session):
        # broadcast when a user leaves
        Room.remove(self, session)
        self.broadcast((session.name + ' has left the room.\n').encode("utf-8"))

    def do_say(self, session, line):
        # send message via client portal
        self.broadcast((session.name + ': ' + line + '\n').encode("utf-8"))

    def do_look(self, session, line):
        # check online users
        session.push(b'Online Users:\n')
        for other in self.sessions:
            session.push((other.name + '\n').encode("utf-8"))
            
if __name__ == '__main__':

    s = ChatServer(PORT)
    try:
        print("chat serve run at '0.0.0.0:{0}'".format(PORT))
        asyncore.loop()
    except KeyboardInterrupt:
        print("chat server exit")