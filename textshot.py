import argparse
import time
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, QTimer
from logger import log_copied, log_ocr_failure
from notifications import notify_copied, notify_ocr_failure
from ocr import ensure_tesseract_installed, get_ocr_result
import sys
import jsonlines
import openai 
from openai import OpenAI

class Snipper(QtWidgets.QWidget):
    def __init__(self, parent, langs=None, flags=Qt.WindowFlags()):
        super().__init__(parent=parent, flags=flags)

        self.setWindowTitle("TextShot")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

        self._screen = QtWidgets.QApplication.screenAt(QtGui.QCursor.pos())
        numofscreenshots = 0 
        palette = QtGui.QPalette()
        palette.setBrush(self.backgroundRole(), QtGui.QBrush(self.getWindow()))
        self.setPalette(palette)

        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        self.start, self.end = QtCore.QPoint(), QtCore.QPoint()
        self.langs = langs

    def getWindow(self):
        return self._screen.grabWindow(0)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QtWidgets.QApplication.quit()

        return super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 100))
        painter.drawRect(0, 0, self.width(), self.height())

        if self.start == self.end:
            return super().paintEvent(event)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 3))
        painter.setBrush(painter.background())
        painter.drawRect(QtCore.QRect(self.start, self.end))
        return super().paintEvent(event)

    def mousePressEvent(self, event):
        self.start = self.end = event.pos()
        self.update()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()
        return super().mousePressEvent(event)

    def snipOcr(self):
        self.hide()

        ocr_result = self.ocrOfDrawnRectangle()
        if ocr_result:
            return ocr_result
        else:
            log_ocr_failure()

    def hide(self):
        super().hide()
        QtWidgets.QApplication.processEvents()

    def ocrOfDrawnRectangle(self):
        return get_ocr_result(
            self.getWindow().copy(
                min(self.start.x(), self.end.x()),
                min(self.start.y(), self.end.y()),
                abs(self.start.x() - self.end.x()),
                abs(self.start.y() - self.end.y()),
            ),
            self.langs,
        )


class OneTimeSnipper(Snipper):
    """Take an OCR screenshot once then end execution."""

    def mouseReleaseEvent(self, event):
        if self.start == self.end:
            return super().mouseReleaseEvent(event)

        ocr_result = self.snipOcr()
        if ocr_result:
            pyperclip.copy(ocr_result)
            log_copied(ocr_result)
            notify_copied(ocr_result)
        else:
            notify_ocr_failure()

        QtWidgets.QApplication.quit()


class IntervalSnipper(Snipper):
    """
    Draw the screenshot rectangle once, then perform OCR there every `interval`
    ms.
    """
	
 
    numofshots = 0
  
   
    prevOcrResult = ""
    def __init__(self, parent, interval, langs=None, flags=Qt.WindowFlags()):
        super().__init__(parent, langs, flags)
        self.interval = interval

        # Initialize the OpenAI client
        self.client = OpenAI()  # This uses OPENAI_API_KEY from environment variables by default

        # This is your chosen Assistant ID
        self.assistant_id= "asst_yddeElSALZ4jKHtrswrT7a7R"
        self.duplicate = False 
        self.numofduplicates = 0


    def get_assistant_response(self, question):
        # Create a Thread
        thread = self.client.beta.threads.create()

        # Add a Message to the Thread
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )

        # Run the Assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )

        # Check the status of the Run and retrieve the response
        while run.status != "completed":
            time.sleep(1)  # Wait for a short period before checking again
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        # Retrieve the Messages added by the Assistant to the Thread
        messages = self.client.beta.threads.messages.list(
            thread_id=thread.id
        )

        # Extract and return the response text
        for message in messages:
            for text_or_image in message.content:
                if text_or_image.type == 'text':
                    return text_or_image.text.value

    def mouseReleaseEvent(self, event):
        if self.start == self.end:
            return super().mouseReleaseEvent(event)

        # Take a shot as soon as the rectangle has been drawn
        self.onShotOcrInterval()
        # And then every `self.interval`ms
        self.startShotOcrInterval()

    def startShotOcrInterval(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.onShotOcrInterval)
        self.timer.start(self.interval)
    def log_saved_to_file(self, file_path):

        # You can customize the log message as needed
        print(f"OCR result saved to file: {file_path}")


    def onShotOcrInterval(self):
        prev_ocr_result = self.prevOcrResult
        ocr_result = self.snipOcr()
        self.numofshots += 1
        
        
        if not ocr_result:
            log_ocr_failure()
            return

        self.prevOcrResult = ocr_result
        
        self.duplicate = False
      
        if prev_ocr_result == ocr_result:
            self.numofshots -= 1
            ocr_result = ""
            self.duplicate = True
            time.sleep(1)
            return
        
                 
        
        # # Separate the logic of gathering the chatbot responses
        # buffer = ""
        # if ocr_result:
        #     print("Question Starts with: " + ocr_result[:7] + " Ends with: " + ocr_result[-7:]) 
        # if self.duplicate == False:
        #     print("---------------------------------------------------------------------")
        #     for data in self.get_assistant_response(ocr_result):
        #         buffer += data
        #         if len(buffer) >= 1500:
        #             print(buffer[:1500].upper())  # Print only the first 1500 characters
        #             buffer = buffer[150:]

        #     if buffer:
        #         print(buffer.upper())
        #     print("------------------------------------------------------------------------" + "\n")
        buffer = ""
        if ocr_result:
            print("Question Starts with: " + ocr_result[:7] + " Ends with: " + ocr_result[-7:]) 
        if self.duplicate == False:
            print("---------------------------------------------------------------------")
            for data in self.get_assistant_response(ocr_result):
                buffer += data

            print(buffer.upper())
            print("------------------------------------------------------------------------" + "\n")

        # Create a dictionary to store the data
        output_data = {"prompt": ocr_result, "buffer": buffer}

        # Write the data to a JSONL file
        with jsonlines.open('output.jsonl', mode='a') as writer:
            writer.write(output_data)
        
          
        

arg_parser = argparse.ArgumentParser(description=__doc__)
arg_parser.add_argument(
    "langs",
    nargs="?",
    default="eng",
    help='languages passed to tesseract, eg. "eng+fra" (default: %(default)s)',
)
arg_parser.add_argument(
    "-i",
    "--interval",
    type=int,
    default=None,
    help="select a screen region then take textshots every INTERVAL milliseconds",
)


def take_textshot(langs, interval):
    ensure_tesseract_installed()

    QtCore.QCoreApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
    app = QtWidgets.QApplication(sys.argv)

    if interval is not None:
        snipper = IntervalSnipper(None, interval, langs)
    else:
        # If you still want to keep OneTimeSnipper
        # snipper = OneTimeSnipper(None, langs)
        # For IntervalSnipper only, you can remove the else block
        pass

    snipper.show()
    sys.exit(app.exec_())

def main():
    args = arg_parser.parse_args()
    ensure_tesseract_installed()
    take_textshot(args.langs, args.interval)

if __name__ == "__main__":
    main()
