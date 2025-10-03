from pywinauto import Application

# Thử attach vào Voicepeak (đang mở sẵn app)
app = Application(backend="uia").connect(title_re=".*Voicepeak.*")

dlg = app.top_window()
# In ra các control để tham khảo
print(dlg.print_control_identifiers())

# Click nút "File"
file_btn = dlg.child_window(title="File", control_type="Button")
file_btn.click_input()

# Nhập text vào ô Edit đầu tiên
edit_box = dlg.child_window(control_type="Edit")
edit_box.set_edit_text("Xin chào, đây là test tự động!")

# Chọn ComboBox "Latest"
combo = dlg.child_window(title="Latest", control_type="ComboBox")
combo.select("Latest")

# Click nút "Male 2"
male_btn = dlg.child_window(title="Male 2", control_type="Button")
male_btn.click_input()

# Lấy giá trị slider "Volume"
slider = dlg.child_window(control_type="Slider")
print("Volume value:", slider.get_value())