import os
import json
from typing import Any, Optional
from pathlib import Path

def readJson(filePath: str) -> dict:
    """
    desc: 读取 json 文件为 dict
    params:
        filePath: json 文件路径
    returns: json 内容，若读取失败返回空字典
    """
    try:
        with open(filePath, "r", encoding="utf-8") as jsonFile:
            jsonContent = json.load(jsonFile)
        return jsonContent
    except Exception as _:
        return {}

def setConfig(key: str, value: Any) -> bool:
    try:
        configFilePath = os.path.join(Path(__file__).parents[1], "config", "config.json")
        Path(os.path.dirname(configFilePath)).mkdir(parents=True, exist_ok=True)

        config = loadConfig()
        keys = key.split(".")
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

        with open(configFilePath, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False

def loadConfig() -> dict:
    configFilePath = os.path.join(Path(__file__).parents[1], "config", "config.json")
    if not os.path.exists(configFilePath):
        raise FileNotFoundError(f"Config file not found: {configFilePath}")

    return readJson(configFilePath)

def getConfig(key: str, default: Optional[Any] = None) -> Any:
    try:
        config = loadConfig()
        keys = key.split(".")
        current = config
        for k in keys:
            if k not in current:
                return default
            current = current[k]
        return current
    except Exception:
        return default