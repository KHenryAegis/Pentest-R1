from pathlib import Path
from pydantic import BaseModel
from pydantic import Field
import os

from dotenv import load_dotenv
load_dotenv()

SCRIPTS = os.environ.get("KALISCRIPTS")


class WriteFile(BaseModel):
    """Write a script or a text into a file. The file will be located in the 
    /root/scripts foolder of Kali machine."""
    content: str = Field(...)
    file_name: str = Field(...)

    def run(self):
        """Write a script in the /root/scripts folder of the Kali container 

        Returns:
            str: observation for the agent
        """
         # 规范化路径，防止重复斜杠
        file_path = Path(SCRIPTS) / self.file_name.lstrip('/')
        
        # 创建父目录（如果不存在）
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w') as file:
            file.write(self.content)
        output = f'File /root/scripts/{self.file_name} correctly saved.'

        return output

    def __str__(self) -> str:
        return f"WriteFile(content='{self.content}', file_name='{self.file_name}')"