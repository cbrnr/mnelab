import sys
import matplotlib
from PyQt5.QtWidgets import QApplication
from mnelab import MainWindow
import multiprocessing as mp


if __name__ == "__main__":
    mp.set_start_method("spawn")  # required for Linux/macOS with PyQt
    matplotlib.use("Qt5Agg")
    app = QApplication(sys.argv)
    app.setApplicationName("MNELAB")
    app.setOrganizationName("cbrnr")
    main = MainWindow()
    if len(sys.argv) > 1:  # open files from command line arguments
        for f in sys.argv[1:]:
            main.load_file(f)
    sys.exit(app.exec_())
