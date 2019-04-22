# encoding: utf-8

"""
File: main.py
Author: Rock Johnson
"""
import os, sys, cv2, time, pyprind, threading

# 字符串帧
class char_frame:
    ascii_char = "$@B%8&WM#*234567890oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "

    # 像素映射到字符
    def pixel_to_char(self, luminance):
        return self.ascii_char[int(luminance / 256 * len(self.ascii_char))]

    # 将普通帧转换为ascii帧
    def convert(self, img, limit_size = -1, fill = False, wrap = False):
        if limit_size != -1 and (img.shape[0] > limit_size[1] or img.shape[1] > limit_size[0]):
            img = cv2.resize(img, limit_size, interpolation=cv2.INTER_AREA)

        ascii_frame = ""
        blank = ""

        if fill:
            blank += " " * (limit_size[0] - img.shape[1])
        if wrap:
            blank += "\n"
        for i in range(img.shape[0]):
            for j in range(img.shape[1]):
                ascii_frame += self.pixel_to_char(img[i, j])
            ascii_frame += blank
        return ascii_frame

# 视频转字符串
class v2_char(char_frame):
    char_video = []
    time_interval = 0.033

    def __init__(self, path):
        if path.endswith("txt"):
            self.load(path)
        else:
            self.gen_char_video(path)

    def gen_char_video(self, file_path):
        self.char_video = []
        cap = cv2.VideoCapture(file_path) # 使用opencv转换视频
        self.time_interval = round(1 / cap.get(5), 3)
        nf = int(cap.get(7))
        print("正在生成字符串视频,请等待...")

        for i in pyprind.prog_bar(range(nf)):
            # 转换颜色空间，第二个参数是转换类型，cv2.COLOR_BGR2GRAY表示从BGR↔Gray
            raw_frame = cv2.cvtColor(cap.read()[1], cv2.COLOR_BGR2GRAY)
            frame = self.convert(raw_frame, os.get_terminal_size(), True)
            self.char_video.append(frame)
        cap.release()

    def export(self, file_path):
        if not self.char_video:
            return
        with open(file_path, 'w') as f:
            for frame in self.char_video:
                f.write(frame + '\n') # 加一个换行符用以分隔每一帧

    def load(self, file_path):
        self.char_video = []

        # 一行即为一帧
        for i in open(file_path):
            self.char_video.append(i[:-1])

    def play(self, stream = 1):
        if not self.char_video:
            return
        if stream == 1 and os.isatty(sys.stdout.fileno()):
            self.stream_out = sys.stdout.write
            self.stream_flush = sys.stdout.flush
        elif stream == 2 and os.isatty(sys.stderr.fileno()):
            self.stream_out = sys.stderr.write
            self.stream_flush = sys.stderr.flush
        elif hasattr(stream, "write"):
            self.streamOut = stream.write
            self.streamFlush = stream.flush

        breakflag = False

        def get_char():
            nonlocal breakflag

            try:
                import msvcrt # 若系统为 windows 则直接调用 msvcrt.getch()
            except ImportError:
                import tty, termios
                fd = sys.stdin.fileno() # 获得标准输入的文件描述符
                old_settings = termios.tcgetattr(fd) # 保存标准输入的属性
                try:
                    tty.setraw(sys.stdin.fileno()) # 设置标准输入为原始模式
                    ch = sys.stdin.read(1) # 读取一个字符
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings) # 恢复标准输入为原来的属性
                if ch:
                    breakflag = True
            else:
                if msvcrt.getch():
                    breakflag = True

        getchar = threading.Thread(target=get_char) # 创建线程
        getchar.daemon = True # 设置为守护线程
        getchar.start() # 启动守护线程
        rows = len(self.char_video[0]) // os.get_terminal_size()[0] # 输出的字符画行数

        for frame in self.char_video:
            if breakflag:
                break  # 接收到输入则退出循环
            self.stream_out(frame)
            self.stream_flush()
            time.sleep(self.time_interval)
            self.stream_out("\033[{}A\r".format(rows - 1)) # 共rows行，光标上移 rows-1 行回到开始处
        self.stream_out("\033[{}B\033[K".format(rows - 1)) # 光标下移 rows-1 行到最后一行，清空最后一行
        for i in range(rows - 1): # 清空最后一帧的所有行（从倒数第二行起）
            self.stream_out("\033[1A") # 光标上移一行
            self.stream_out("\r\033[K") # 清空光标所在行
        if breakflag:
            self.stream_out("用户打断了!\n")
        else:
            self.stream_out("播放完成!\n")


if __name__ == '__main__':
    v2char = v2_char("./video.mp4")
    v2char.play()