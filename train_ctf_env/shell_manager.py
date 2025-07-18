import docker
import sys
import time
import threading
import select
import re

class PersistentDockerShell:
    def __init__(self, container: docker.models.containers.Container, shell_cmd: str = "/bin/bash"):
        if not isinstance(container, docker.models.containers.Container):
            raise TypeError()
            
        self.container = container
        self.shell_cmd = shell_cmd
        self.exec_id = None
        self.sock = None
        self.running = False
        self.output_buffer = ""
        self.buffer_lock = threading.Lock()
        self.read_thread = None

    def connect(self):
        if self.running:
            print("Shell is already connected.")
            return

        api = self.container.client.api
        self.exec_id = api.exec_create(
            container=self.container.id,
            cmd=self.shell_cmd,
            stdin=True, tty=True, stdout=True, stderr=True
        )["Id"]

        self.sock = api.exec_start(
            exec_id=self.exec_id,
            detach=False, tty=True, socket=True
        )
        self.sock._sock.setblocking(False)

        self.running = True
        self.output_buffer = ""
        self.read_thread = threading.Thread(
            target=self._read_output, daemon=True
        )
        self.read_thread.start()

        time.sleep(0.1)
        self.sock._sock.send(b"stty -echo\n")
        self.sock._sock.send(
            b"bind 'set enable-bracketed-paste off'\n"
        )
        time.sleep(0.1)
        with self.buffer_lock:
            self.output_buffer = ""

    def _read_output(self):
        while self.running:
            try:
                rlist, _, _ = select.select([self.sock._sock], [], [], 0.1)
                if rlist:
                    data = self.sock._sock.recv(4096)
                    if not data:
                        self.running = False
                        break
                    text = data.decode(errors='ignore')
                    with self.buffer_lock:
                        self.output_buffer += text
            except Exception:
                self.running = False
                break

    def send(self, cmd: str, timeout: float = 60.0) -> str:
        with self.buffer_lock:
            self.output_buffer = ""

        sentinel = "__CMD_DONE__"
        full_cmd = cmd.rstrip() + f"\necho {sentinel} $?\n"

        self.sock._sock.send(full_cmd.encode())

        start_time = time.time()
        exit_code = None
        collected = ""
        timed_out = False
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                timed_out = True
                self.sock._sock.send(b'\x03\n')
                time.sleep(1)
                break
                
            with self.buffer_lock:
                buf = self.output_buffer
                
            if sentinel in buf:
                before, after = buf.split(sentinel, 1)
                collected = before
                m = re.search(rf"{sentinel}\s+(\d+)", buf)
                if m:
                    exit_code = int(m.group(1))
                with self.buffer_lock:
                    self.output_buffer = after
                break
                
            time.sleep(0.05)

        if collected or not timed_out:
            lines = collected.splitlines()
            if lines and lines[0].strip() == cmd.splitlines()[0].strip():
                lines = lines[1:]
            stdout = "\n".join(lines).strip()
        else:
            with self.buffer_lock:
                stdout = self.output_buffer.strip()
                if not stdout:
                    raise TimeoutError(f"Command timed out after {timeout}s with no output")
                else:
                    stdout = stdout.strip()
                    if 'Traceback' in stdout:
                        exit_code = 1  
                    else:
                        exit_code = 0

        return exit_code, stdout

    def disconnect(self):
        if not self.running:
            return
            
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=1.0)
            
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass 
                
        self.exec_id = None
        self.sock = None
        print("Shell disconnected.")