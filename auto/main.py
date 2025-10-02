from pywinauto import Application

# Thử attach vào Voicepeak (đang mở sẵn app)
app = Application(backend="uia").connect(title_re=".*Voicepeak.*")

dlg = app.top_window()
print(dlg.print_control_identifiers())