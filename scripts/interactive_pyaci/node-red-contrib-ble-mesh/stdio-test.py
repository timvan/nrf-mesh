import sys

class StdioTest(object):

    def __init__(self):
        self.keep_runing = True

    def run(self):
        while self.keep_runing:
            msg = sys.stdin.readline()
            msg = msg.strip("\n")
            self.handle_message(msg)
            

    def handle_message(self, msg):
        if msg == "echo":
             print("Hii")
        else:
            print("other")

        sys.stdout.flush()

if __name__ == "__main__":
    s = StdioTest()
    s.run()
