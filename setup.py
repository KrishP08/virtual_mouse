from setuptools import setup, find_packages

setup(
    name="virtual_mouse",
    version="0.1.0",
    author="Yax Patel",
    author_email="7233kp@gmail.com",
    description="Control your PC mouse using hand gestures via webcam",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/KrishP08/virtual_mouse",
    packages=find_packages(),
    install_requires=[
        "mediapipe",
        "opencv-python",
        "numpy",
        "customtkinter",
        "pyautogui",
        "pynput",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8, <4",
)
