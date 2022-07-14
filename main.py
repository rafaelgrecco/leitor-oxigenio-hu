from ast import Not
import shutil
from tkinter import EXCEPTION
import numpy as np
import base64
import requests
import imutils
import os
import cv2
import json
import uuid
import random
import time
from loguru import logger
import traceback
import re
import pymongo
from pymongo import MongoClient

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = '.env/ieeeocr-fa4d9584e605.json'


class ERROR_UPLOAD_DATABASE(Exception):
    """Exceptions raised when the upload to mongodb failed

    Returns:
         Exception (_str_): returns a string explaning the exception
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    def __str__(self) -> str:
        return f"Error in upload to database mongo, data do erro: {self.datetime}"


class ANY_NUMBER_RETURNED(Exception):
    """Exceptions raised when any number returned from regex

    Args:
        Exception (_str_): returns a string explaning the exception
    """

    def __init__(self, text) -> None:
        self.text = text

    def __str__(self) -> str:
        return f"Any number found in text: {self.text}"


class MANY_FILES_IN_ROOT_FOLDER(Exception):
    """Exception raised when teh folder original has more than one file

    Args:
        Exception (_str_): returns a string explaning the exception
    """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)

    def __str__(self) -> str:
        return "There is more than one file in the original folder"


class LeitorOxigenio():
    """This is a initial class that performs a extraction of a text from an image
       using google vision api and upload the text extracted to mongodb database
    """

    def __init__(self) -> None:
        self.img_path_original = self._get_path_img()
        self.img_path_processed = os.path.abspath('./images/tmp')
        self.datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    def pre_processing(self):
        """Performs the pre processing in image, apply gray scale and billateral filter

        Returns:
            full_path_processed_img (_str_): full path of the image processed
        """
        # this snippet apply a basic transformations in image
        img = cv2.imread(self.img_path_original, cv2.IMREAD_REDUCED_COLOR_2)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_img = cv2.bilateralFilter(gray_img, 13, 5, 5)

        # this snippet save the image processed on tmp folder (created by save_img function)
        self._save_img()
        name_new_img = uuid.uuid4()
        full_path_processed_img = f"./images/tmp/{name_new_img}.png"
        cv2.imwrite(full_path_processed_img, gray_img)
        return full_path_processed_img

    def detect_text(self, path):
        """Detects text in the file.

            Args:
                path: The full path of image processed

            Returns:
                text_img(_str_): Text extracted from image using google vision api
        """
        from google.cloud import vision
        import io
        client = vision.ImageAnnotatorClient()

        with io.open(path, 'rb') as image_file:
            content = image_file.read()

        image = vision.Image(content=content)

        response = client.text_detection(image=image)
        texts = response.text_annotations

        if response.error.message:
            raise Exception(
                f'{response.error.message}\nFor more info on error messages, check: '
                'https://cloud.google.com/apis/design/errors')

        text_img = f'{texts[0].description}'
        return text_img

    def _get_path_img(self):
        """Search images in folder of original images.

        Returns:
            full_path(str): full path of original image
        """
        for arquivo in os.listdir("images/original"):
            if len(os.listdir("images/original")) > 1:
                raise MANY_FILES_IN_ROOT_FOLDER
            else:
                return f"images/original/{arquivo}"

    def _save_img(self):
        """Checks if the tmp folder exists, if not, it will create it.
        """
        if not os.path.exists(self.img_path_processed):
            os.mkdir(self.img_path_processed)

    def _get_numbers(self, text):
        """Extract the numbers in string returned by google api

        Args:
            text(_str_): string contain full text extracted

        Returns:
           numbers(_tuple_): numbers found on text
        """
        try:
            numbers = [number for number in re.findall(
                r'-?\d{4}.?\d{1}', text)]
        except ANY_NUMBER_RETURNED(text):
            logger.error(traceback.format_exc())
            pass
        return numbers

    def clean_folders(self):
        """Clean folders created
        """

        # this snippet clean the folder original
        os.remove(f"{self.img_path_original}")

        # this snippet delete the tmp folder and your files
        if os.path.exists(self.img_path_processed):
            shutil.rmtree(self.img_path_processed)

    def connect_mongo(self, post):
        """Perform the upload of text extracted to mongodb database

        Args:
            post(_dict_): A dictionary containing the variables to upload in database mongo
        """
        cluster = "mongodb+srv://rafael:ky6FjS0nE2vcLzOn@cluster0.nifc0.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(cluster)
        db = client['ieeeHU']
        data = db.dados
        try:
            data.insert_one(post)
            logger.success(
                f"Upload realizado, data da operação: {self.datetime}")
        except(ERROR_UPLOAD_DATABASE):
            logger.error(traceback.format_exc())
            pass

    def main(self):
        image_processed_path = self.pre_processing()
        text = self.detect_text(image_processed_path)
        numbers = self._get_numbers(text)
        logger.info(f"Números extraídos: {numbers}")
        post = {"n1": numbers[0], "p1": numbers[1], "datetime": self.datetime}
        logger.add(f"logs/file_{self.datetime}.log")
        self.connect_mongo(post)
        self.clean_folders()


if __name__ == "__main__":
    run = LeitorOxigenio()
    run.main()
