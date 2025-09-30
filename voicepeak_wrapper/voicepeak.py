# Copyright (c) 2023 Nanahuse
# Phần mềm này được phát hành theo giấy phép MIT
# https://opensource.org/license/mit/

import asyncio
from dataclasses import dataclass
import os


@dataclass
class Narrator(object):
    name: str
    emotions: tuple[str, ...]


class Voicepeak:
    def __init__(
        self,
        exe_path: str = os.path.join(os.environ["ProgramFiles"], "VOICEPEAK", "voicepeak.exe"),
    ):
        """
        Nếu bạn cài đặt VOICEPEAK ở vị trí không phải mặc định, hãy chỉ định exe_path.

        Tham số:
            exe_path (str, optional): Đường dẫn đến voicepeak.exe. Mặc định là vị trí cài đặt tiêu chuẩn.
        """

        if not os.path.exists(exe_path):
            raise FileNotFoundError("Không tìm thấy file thực thi VOICEPEAK")
        self.__exe_path = exe_path

    async def __async_run(self, cmd: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            f'"{self.__exe_path}" {cmd}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if len(stderr) != 0:
            error_message = stderr.decode()
            raise RuntimeError(error_message)

        return stdout.decode()

    def __make_say_command(
        self,
        text: str | None = None,
        text_file: str | None = None,
        output_path: str | None = None,
        narrator: Narrator | str | None = None,
        emotions: dict[str, int] | None = None,
        speed: int | None = None,
        pitch: int | None = None,
    ) -> str:
        command = list()

        match text, text_file:
            case str(), str():
                raise ValueError("Chỉ được chỉ định một trong hai: text hoặc text_file")
            case str(), None:
                command.append(f'-s "{text}"')
            case None, str():
                command.append(f'-t "{text_file}"')
            case None, None:
                raise ValueError("Cần thiết lập text hoặc text_file.")
            case _:
                raise ValueError("Giá trị text hoặc text_file không hợp lệ.")

        if output_path is not None:
            command.append(f'-o "{output_path}"')

        match narrator:
            case Narrator():
                command.append(f'-n "{narrator.name}"')
            case str():
                command.append(f'-n "{narrator}"')
            case None:
                pass

        if emotions is not None:
            command.append(f'-e {" ,".join(f"{param}={value}" for param, value in emotions.items())}')

        SPEED_RANGE = (50, 200)
        if isinstance(speed, int) and (SPEED_RANGE[0] <= speed <= SPEED_RANGE[1]):
            command.append(f"--speed {speed}")
        elif speed is None:
            pass
        else:
            raise ValueError(f"speed phải là số nguyên trong khoảng {SPEED_RANGE[0]} - {SPEED_RANGE[1]}")

        PITCH_RANGE = (-300, 300)
        if isinstance(pitch, int) and (PITCH_RANGE[0] <= pitch <= PITCH_RANGE[1]):
            command.append(f"--pitch {pitch}")
        elif pitch is None:
            pass
        else:
            raise ValueError(f"pitch phải là số nguyên trong khoảng {PITCH_RANGE[0]} - {PITCH_RANGE[1]}")

        return " ".join(command)

    async def say_text(
        self,
        text: str,
        *,
        output_path: str | None = None,
        narrator: Narrator | str | None = None,
        emotions: dict[str, int] | None = None,
        speed: int | None = None,
        pitch: int | None = None,
    ):
        """
        Lưu file wav đọc văn bản.

        Tham số:
            text (str): Văn bản cần đọc

            output_path (str | None, optional): Đường dẫn lưu file wav. Nếu không chỉ định sẽ tạo file output.wav cùng thư mục với voicepeak.exe. Mặc định: None.

            narrator (Narrator | str | None, optional): Loại narrator đọc. Có thể truyền kiểu Narrator hoặc tên dạng str. Mặc định: None.

            emotions (dict[str, int] | None, optional): Chỉ định cảm xúc khi đọc. Dạng dict {"tên cảm xúc":giá trị}. Mặc định: None.

            speed (int | None, optional): Tốc độ đọc. 100 là bình thường. Khoảng 50~200. Mặc định: None.

            pitch (int | None, optional): Cao độ đọc. 0 là bình thường. Khoảng -300~300. Mặc định: None.
        """
        return await self.__async_run(
            self.__make_say_command(
                text=text,
                output_path=output_path,
                narrator=narrator,
                emotions=emotions,
                speed=speed,
                pitch=pitch,
            )
        )

    async def say_textfile(
        self,
        text_path: str,
        *,
        output_path: str = "./output.wav",
        narrator: Narrator | str | None = None,
        emotions: dict[str, int] | None = None,
        speed: int | None = None,
        pitch: int | None = None,
    ):
        """
        Lưu file wav đọc nội dung từ file văn bản.

        Tham số:
            text_path (str): Đường dẫn file văn bản cần đọc

            output_path (str , optional): Đường dẫn lưu file wav. Mặc định là output.wav.

            narrator (Narrator | str | None, optional): Loại narrator đọc. Có thể truyền kiểu Narrator hoặc tên dạng str. Mặc định: None.

            emotions (dict[str, int] | None, optional): Chỉ định cảm xúc khi đọc. Dạng dict {"tên cảm xúc":giá trị}. Mặc định: None.

            speed (int | None, optional): Tốc độ đọc. 100 là bình thường. Khoảng 50~200. Mặc định: None.

            pitch (int | None, optional): Cao độ đọc. 0 là bình thường. Khoảng -300~300. Mặc định: None.
        """
        return await self.__async_run(
            self.__make_say_command(
                text_file=text_path,
                output_path=output_path,
                narrator=narrator,
                emotions=emotions,
                speed=speed,
                pitch=pitch,
            )
        )

    async def get_narrator_list(self) -> tuple[Narrator, ...]:
        """
        Lấy danh sách narrator và các cảm xúc của từng narrator.

        Trả về:
            tuple[Narrator]: Danh sách narrator
        """
        narrators = await self.get_narrator_name_list()
        narrator_list = list()
        for name in narrators:
            emotions = await self.get_emotion_list(name)
            narrator_list.append(Narrator(name, emotions))
        return tuple(narrator_list)

    async def get_narrator_name_list(self) -> tuple[str, ...]:
        """
        Lấy danh sách tên narrator có thể sử dụng.

        Trả về:
            tuple[str]: Danh sách tên narrator
        """
        return tuple(tmp for tmp in (await self.__async_run("--list-narrator")).splitlines())

    async def get_emotion_list(self, name: str) -> tuple[str, ...]:
        """
        Lấy danh sách tên cảm xúc của narrator.

        Tham số:
            name (str): Tên narrator

        Trả về:
            tuple[str]: Danh sách tên cảm xúc của narrator
        """
        return tuple(tmp for tmp in (await self.__async_run(f'--list-emotion "{name}"')).splitlines())
