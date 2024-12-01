from PyQt6.QtWidgets import QLabel, QHBoxLayout, QWidget
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from ..otsconfig import config

class LabelWithThumb(QWidget):
    def __init__(self, label, thumb_url):
        super().__init__()

        self.aspect_ratio = config.get("search_thumb_height")

        # Create a horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(10)  # Set spacing between widgets

        # Create the QLabel for the text
        item_label = QLabel(self)
        item_label.setText(label.strip())
        item_label.setWordWrap(True)  # Allow text to wrap if necessary
        item_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Create the QLabel for the pixmap
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(self.aspect_ratio, self.aspect_ratio)  # Set fixed size for the image label

        # Create QNetworkAccessManager
        self.manager = QNetworkAccessManager(self)
        request = QNetworkRequest(QUrl(thumb_url))

        # Connect the finished signal to the slot
        self.manager.finished.connect(self.on_finished)
        self.manager.get(request)  # Make the request

        # Add both labels to the layout
        layout.addWidget(self.image_label)
        layout.addWidget(item_label)

        self.setLayout(layout)

    def on_finished(self, reply: QNetworkReply):
        # This method is called when the network request is completed
        if reply.error() == QNetworkReply.NetworkError.NoError:  # Correct error checking
            # Read the image data and create a pixmap
            image_data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            scaled_pixmap = pixmap.scaled(self.aspect_ratio, self.aspect_ratio, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)  # Update the QLabel with the pixmap

        # Mark request for deletion
        self.manager.deleteLater()
        reply.deleteLater()
