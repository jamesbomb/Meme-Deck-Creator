import sys
import os
import csv
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtGui import QPixmap, QPainter, QFontDatabase
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog,
    QComboBox, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit, QMessageBox, QFontDialog, QSlider, QGridLayout
)
from PyQt6.QtCore import Qt, QRect
from rich.console import Console

console = Console()

class DraggableTextLabel(QLabel):
    """
    QLabel subclass that allows vertical dragging of the text within its parent.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("QLabel { background-color : transparent; }")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dragging = False
        self.offset = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.position().y()
            console.print("[green]Inizio trascinamento testo.[/green]")

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_y = self.y() + event.position().y() - self.offset
            parent_height = self.parent().height()
            label_height = self.height()
            padding = self.parent().parent().padding_value

            # Limita il movimento solo verticalmente
            new_y = max(padding, min(new_y, parent_height - label_height - padding))
            self.move(self.x(), new_y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            console.print("[green]Fine trascinamento testo.[/green]")

class CardGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generatore di Mazzi di Carte")

        self.background_image = None
        self.phrases = []
        self.current_index = 0
        self.save_folder = ""
        self.current_font = "Arial"
        self.padding_value = 10

        self.init_ui()
        
        # Imposta la dimensione massima della finestra
        self.set_max_window_size()

    def set_max_window_size(self):
        # Ottiene la risoluzione dello schermo
        screen = QtWidgets.QApplication.primaryScreen()
        screen_size = screen.size()
        self.setMaximumSize(screen_size)
        self.setMinimumSize(1024, 768)

    def init_ui(self):
        # Layout principale diviso verticalmente
        main_layout = QHBoxLayout()

        # *** Sezione Preview (Sinistra) ***
        preview_layout = QVBoxLayout()

        # Area di visualizzazione dell'immagine
        self.image_label = QLabel("Carica un'immagine di background")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("QLabel { background-color : lightgray; }")
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setAcceptDrops(True)
        self.image_label.installEventFilter(self)
        self.image_label.setScaledContents(False)

        # Draggable Text Label
        self.text_label = DraggableTextLabel(self.image_label)
        self.text_label.setText("")
        self.text_label.setWordWrap(True)
        self.text_label.setGeometry(10, 10, self.image_label.width() - 20, 50)
        self.text_label.hide()

        preview_layout.addWidget(self.image_label)

        # *** Sezione Controlli (Destra) ***
        controls_layout = QVBoxLayout()

        # Grid layout per i pulsanti
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(10)

        # Bottoni di controllo
        load_image_btn = QPushButton("Carica Immagine")
        load_image_btn.clicked.connect(self.load_background_image)

        load_phrases_btn = QPushButton("Carica Frasi")
        load_phrases_btn.clicked.connect(self.load_phrases)

        reset_phrases_btn = QPushButton("Reset Frasi")
        reset_phrases_btn.clicked.connect(self.reset_phrases)

        select_folder_btn = QPushButton("Seleziona Cartella")
        select_folder_btn.clicked.connect(self.select_save_folder)

        # Adjust button sizes
        button_width = 150
        button_height = 60
        for btn in [load_image_btn, load_phrases_btn, reset_phrases_btn, select_folder_btn]:
            btn.setFixedSize(button_width, button_height)

        # Add buttons to grid layout
        buttons_layout.addWidget(load_image_btn, 0, 0)
        buttons_layout.addWidget(load_phrases_btn, 0, 1)
        buttons_layout.addWidget(reset_phrases_btn, 1, 0)
        buttons_layout.addWidget(select_folder_btn, 1, 1)

        controls_layout.addLayout(buttons_layout)

        # Slider per la scalatura del testo
        self.text_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_scale_slider.setRange(10, 100)
        self.text_scale_slider.setValue(20)
        self.text_scale_slider.setTickInterval(10)
        self.text_scale_slider.valueChanged.connect(self.update_preview)

        controls_layout.addWidget(QLabel("Scalatura Testo (%)"))
        controls_layout.addWidget(self.text_scale_slider)

        # Scelta del Font
        self.font_button = QPushButton("Scegli Font")
        self.font_button.clicked.connect(self.choose_font)
        self.font_button.setFixedSize(button_width, button_height)

        self.font_label = QLabel(f"Font Attuale: {self.current_font}")

        controls_layout.addWidget(self.font_button)
        controls_layout.addWidget(self.font_label)

        # Allineamento del testo
        self.alignment_combo = QComboBox()
        self.alignment_combo.addItems(["Sinistra", "Centro", "Destra"])
        self.alignment_combo.setCurrentText("Centro")
        self.alignment_combo.currentIndexChanged.connect(self.update_preview)

        controls_layout.addWidget(QLabel("Allineamento Testo"))
        controls_layout.addWidget(self.alignment_combo)

        # Padding
        padding_layout = QHBoxLayout()
        padding_label = QLabel("Padding (px)")
        self.padding_input = QLineEdit(str(self.padding_value))
        self.padding_input.setValidator(QtGui.QIntValidator(0, 100))
        self.padding_input.textChanged.connect(self.update_preview)
        self.padding_input.setFixedWidth(30)
        
        padding_layout.addWidget(padding_label)
        padding_layout.addWidget(self.padding_input)
        padding_layout.addStretch()
        controls_layout.addLayout(padding_layout)

        # Navigazione tra le frasi
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("Precedente")
        prev_btn.clicked.connect(self.prev_phrase)
        next_btn = QPushButton("Successiva")
        next_btn.clicked.connect(self.next_phrase)
        prev_btn.setFixedSize(button_width, button_height)
        next_btn.setFixedSize(button_width, button_height)
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        controls_layout.addLayout(nav_layout)

        # Aggiungi spazio vuoto per allineare i controlli in alto
        controls_layout.addStretch()

        # Pulsante "Genera Mazzo" in fondo e colorato di blu
        generate_deck_btn = QPushButton("Genera Mazzo")
        generate_deck_btn.clicked.connect(self.generate_deck)
        generate_deck_btn.setStyleSheet("background-color: blue; color: white;")
        generate_deck_btn.setFixedSize(button_width * 2, button_height)
        controls_layout.addWidget(generate_deck_btn, alignment=Qt.AlignmentFlag.AlignBottom)

        # Aggiunta delle sezioni al layout principale
        main_layout.addLayout(preview_layout, 2)  # Occupano 2/3 della finestra
        main_layout.addLayout(controls_layout, 1)  # Occupano 1/3 della finestra

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Imposta la dimensione iniziale della finestra
        self.resize(1024, 768)

    def eventFilter(self, source, event):
        # Gestione del drag & drop per l'immagine
        if source == self.image_label:
            if event.type() == QtCore.QEvent.Type.DragEnter:
                if event.mimeData().hasImage():
                    event.accept()
                else:
                    event.ignore()
                return True
            elif event.type() == QtCore.QEvent.Type.Drop:
                if event.mimeData().hasImage():
                    url = event.mimeData().urls()[0]
                    self.set_background_image(url.toLocalFile())
                    event.accept()
                else:
                    event.ignore()
                return True
        return super().eventFilter(source, event)

    def load_background_image(self):
        # Carica l'immagine di background
        options = QFileDialog.Option.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Seleziona Immagine di Background", "", "Immagini (*.png *.jpg *.jpeg *.bmp)", options=options
        )
        if file_name:
            self.set_background_image(file_name)

    def set_background_image(self, file_path):
        # Imposta l'immagine di background e ridimensiona il riquadro
        self.background_image = QPixmap(file_path)
        if self.background_image.isNull():
            QMessageBox.critical(self, "Errore", "Immagine non valida o danneggiata.")
            console.print(f"[red]Errore:[/red] Immagine non valida: {file_path}")
            return

        max_preview_height = 768

        # Calcola la scala necessaria per adattare l'immagine
        scale_factor = min(max_preview_height / self.background_image.height(), 1)

        scaled_width = int(self.background_image.width() * scale_factor)
        scaled_height = int(self.background_image.height() * scale_factor)
        scaled_image = self.background_image.scaled(
            scaled_width,
            scaled_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Imposta le dimensioni del riquadro in base all'immagine scalata
        self.image_label.setFixedSize(scaled_image.width(), scaled_image.height())
        self.image_label.setPixmap(scaled_image)
        console.print(f"[green]Immagine di background caricata e scalata:[/green] {file_path}")

        # Posiziona il testo centrato verticalmente
        self.update_preview()

    def load_phrases(self):
        # Carica le frasi da un file
        options = QFileDialog.Option.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Seleziona File di Frasi", "", "Testo (*.txt *.csv)", options=options
        )
        if file_name:
            self.read_phrases_from_file(file_name)

    def read_phrases_from_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                if file_path.endswith('.txt'):
                    self.phrases = [line.strip() for line in file if line.strip()]
                elif file_path.endswith('.csv'):
                    reader = csv.reader(file)
                    self.phrases = [row[0].strip() for row in reader if row and row[0].strip()]
            self.current_index = 0
            console.print(f"[green]File di frasi caricato:[/green] {file_path}")
            console.print(f"[blue]Numero di frasi caricate:[/blue] {len(self.phrases)}")

            # Aggiorna il testo visualizzato
            if self.phrases:
                self.update_preview()
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore durante il caricamento delle frasi: {e}")
            console.print(f"[red]Errore durante il caricamento delle frasi:[/red] {e}")

    def reset_phrases(self):
        # Resetta le frasi attuali
        self.phrases = []
        self.current_index = 0
        self.text_label.setText("")
        self.update_preview()
        console.print("[yellow]Frasi resettate.[/yellow]")

    def select_save_folder(self):
        # Seleziona la cartella di salvataggio
        folder = QFileDialog.getExistingDirectory(self, "Seleziona Cartella di Salvataggio")
        if folder:
            self.save_folder = folder
            console.print(f"[green]Cartella di salvataggio selezionata:[/green] {folder}")

    def choose_font(self):
        # Apri il dialogo per la scelta del font
        font, ok = QFontDialog.getFont()
        if ok:
            self.current_font = font.family()
            console.print(f"[green]Font selezionato:[/green] {self.current_font}")
            self.font_label.setText(f"Font Attuale: {self.current_font}")
            self.text_label.setFont(font)
            self.update_preview()

    def update_preview(self):
        # Aggiorna l'anteprima dell'immagine con il testo
        if self.background_image:
            try:
                self.padding_value = int(self.padding_input.text())
            except ValueError:
                self.padding_value = 10

            self.text_label.setFixedWidth(self.image_label.width() - 2 * self.padding_value)

            font_size = self.text_scale_slider.value()
            font = QtGui.QFont(self.current_font, font_size)
            self.text_label.setFont(font)

            alignment = self.alignment_combo.currentText()
            if alignment == "Sinistra":
                align_flag = Qt.AlignmentFlag.AlignLeft
            elif alignment == "Destra":
                align_flag = Qt.AlignmentFlag.AlignRight
            else:
                align_flag = Qt.AlignmentFlag.AlignCenter
            self.text_label.setAlignment(align_flag)

            # Posiziona il testo
            if self.phrases:
                self.text_label.setText(self.phrases[self.current_index])
                self.text_label.adjustSize()

                self.text_label.setWordWrap(True)

                self.center_text_label()
                self.text_label.show()
            else:
                self.text_label.setText("")
                self.text_label.hide()
        else:
            self.text_label.setText("")
            self.text_label.hide()

    def center_text_label(self):
        # Centra verticalmente il testo all'interno dell'immagine
        label_height = self.text_label.height()
        image_height = self.image_label.height()
        new_y = (image_height - label_height) // 2
        padding = self.padding_value
        new_y = max(padding, min(new_y, image_height - label_height - padding))
        self.text_label.move(self.padding_value, new_y)

    def prev_phrase(self):
        # Mostra la frase precedente
        if self.phrases:
            self.current_index = (self.current_index - 1) % len(self.phrases)
            self.update_preview()
            console.print(f"[blue]Visualizzata frase {self.current_index + 1}/{len(self.phrases)}[/blue]")

    def next_phrase(self):
        # Mostra la frase successiva
        if self.phrases:
            self.current_index = (self.current_index + 1) % len(self.phrases)
            self.update_preview()
            console.print(f"[blue]Visualizzata frase {self.current_index + 1}/{len(self.phrases)}[/blue]")

    def generate_deck(self):
        # Genera e salva il mazzo di carte
        if not self.save_folder:
            QMessageBox.warning(self, "Errore", "Seleziona una cartella di salvataggio.")
            console.print("[red]Errore:[/red] Nessuna cartella di salvataggio selezionata.")
            return

        if not self.background_image or not self.phrases:
            QMessageBox.warning(self, "Errore", "Assicurati di aver caricato un'immagine e delle frasi.")
            console.print("[red]Errore:[/red] Immagine o frasi mancanti.")
            return

        # Conferma prima di iniziare la generazione
        reply = QMessageBox.question(
            self, 'Conferma Generazione', 
            f"Sei sicuro di voler generare {len(self.phrases)} carte?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        console.print("[yellow]Inizio generazione del mazzo...[/yellow]")

        for index, phrase in enumerate(self.phrases):
            try:
                final_image = self.background_image.copy()
                painter = QPainter(final_image)

                font_size = self.text_scale_slider.value()
                font = QtGui.QFont(self.current_font, font_size)
                painter.setFont(font)

                alignment = self.alignment_combo.currentText()
                if alignment == "Sinistra":
                    align_flag = Qt.AlignmentFlag.AlignLeft
                elif alignment == "Destra":
                    align_flag = Qt.AlignmentFlag.AlignRight
                else:
                    align_flag = Qt.AlignmentFlag.AlignCenter

                padding = self.padding_value

                rect = QRect(
                    padding,
                    padding,
                    final_image.width() - 2 * padding,
                    final_image.height() - 2 * padding
                )

                painter.drawText(
                    rect,
                    align_flag | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                    phrase
                )
                painter.end()

                file_path = os.path.join(self.save_folder, f"card_{index + 1}.png")
                final_image.save(file_path)
                console.print(f"[green]Immagine salvata:[/green] {file_path}")

            except Exception as e:
                console.print(f"[red]Errore durante la generazione della carta {index + 1}:[/red] {e}")

        QMessageBox.information(self, "Successo", "Mazzo generato con successo!")
        console.print("[blue]Generazione del mazzo completata con successo.[/blue]")

def main():
    app = QApplication(sys.argv)
    window = CardGenerator()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
