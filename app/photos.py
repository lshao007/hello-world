import datetime
import hashlib

import cv2
import numpy
import uuid

from flask import render_template, redirect, url_for, request, g, session
from wand.image import Image
import os
from app import s3
from app import webapp
from app.db import get_db

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
TYPE_ORIGINAL = 1
TYPE_THUMBNAIL = 2
TYPE_FACE_DETECTED = 3

face_cascade = cv2.CascadeClassifier(os.path.join(cv2.haarcascades, 'haarcascade_frontalface_default.xml'))

@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@webapp.route('/', methods=['GET'])
@webapp.route('/album', methods=['GET'])
#Return html with thumbnails of all photos for the current user
def thumbnails():
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    session['request'] = session['request'] + 1
    cnx = get_db()

    cursor = cnx.cursor()

    query = "SELECT p.id, t.filename " \
            "FROM photo p, storedphoto t " \
            "WHERE p.id = t.photo_id AND " \
            "      t.type_id = 2 AND " \
            "      p.userId = %s "

    try:
        cursor.execute(query, (session['user_id'],))
    except Exception as e:
        return e.msg

    return render_template("photos/album.html",cursor=cursor)

@webapp.route('/photo/<int:photo_id>',methods=['GET'])
#Return html with alls the versions of a given photo
def details(photo_id):
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    session['request'] = session['request'] + 1
    try:
        cnx = get_db()
        cursor = cnx.cursor()

        # create a new tuple for the photo and store the
        query = "SELECT t.filename " \
                "FROM storedphoto t, photo p " \
                "WHERE t.photo_id = p.id AND " \
                "      p.id = %s AND " \
                "      p.userId = %s AND " \
                "      t.type_id IN (1,3)"
        cursor.execute(query, (photo_id,session['user_id']))

    except Exception as e:
            return e.msg

    return render_template("photos/details.html",cursor=cursor)




@webapp.route('/upload_form',methods=['GET'])
#Returns an html form for uploading a new photo
def upload_form():
    if 'authenticated' not in session:
        return redirect(url_for('login'))
    session['request'] = session['request'] + 1
    e = None

    if 'error' in session:
        e = session['error']
        session.pop('error')


    return render_template("photos/upload_form.html", error=e)



def filename_extension(filename):
    _, file_extension = os.path.splitext(filename)
    return file_extension[1:]

def is_allowed_file(filename):
    return '.' in filename and filename_extension(filename) in ALLOWED_EXTENSIONS


@webapp.route('/upload_save', methods=['POST'])
#Handles photo upload and the creation of a thumbnail and three transformations
def upload_save():
    if 'authenticated' not in session:
        return redirect(url_for('upload_form'))
    session['request'] = session['request'] + 1
    # check if the post request has the file part
    if 'uploadedfile' not in request.files:
        session['error'] = "Missing uploaded file"
        return redirect(url_for('upload_form'))

    new_file = request.files['uploadedfile']

    # if user does not select file, browser also
    # submit a empty part without filename
    if new_file.filename == '':
        session['error'] = 'Missing file name'
        return redirect(url_for('upload_form'))

    if is_allowed_file(new_file.filename) == False:
        session['error'] = 'File type not supported'
        return redirect(url_for('upload_form'))

    try:
        process_file(session['user_id'], new_file)
    except Exception as e:
        session['error'] = 'Unable to process file: ' + e
        return redirect(url_for('upload_form'))

    return redirect(url_for('thumbnails'))


def process_file(user_id, new_file):
    store_base = "I" + datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '-' + str(uuid.uuid4())
    store_ext = filename_extension(new_file.filename)
    storename=store_base + "." + store_ext
    storepath='app/static/user_images'
    onlinepath='https://s3.amazonaws.com/a2s3pub/'
    original_store_path = os.path.join(storepath, storename)
    online_store_path= os.path.join(onlinepath, storename)
    new_file.save(original_store_path)
    s3.upload_file(storename,original_store_path)
    try:
        cnx = get_db()
        cursor = cnx.cursor()

        # create a new tuple for the photo and store the
        query = "INSERT INTO photo (userId) VALUES (%s)"
        cursor.execute(query, (user_id,))

        # get id of newly created tuple
        query = "SELECT LAST_INSERT_ID()"
        cursor.execute(query)

        row = cursor.fetchone()

        photo_id = row[0]

        # store the path to the original image
        query = "INSERT INTO storedphoto (filename,type_id,photo_id) VALUES (%s,%s,%s)"

        cursor.execute(query, (online_store_path, TYPE_ORIGINAL, photo_id))

        # create thumbnail
        img = Image(filename=original_store_path)
        i = img.clone()
        i.resize(80, 80)
        storethumbname = store_base + "_thumb." + store_ext
        thumbnail_online_path = os.path.join(onlinepath, storethumbname)
        thumbnail_store_path = os.path.join('app/static/user_images', storethumbname)
        i.save(filename=thumbnail_store_path)
        s3.upload_file(storethumbname,thumbnail_store_path)

        # store path to thumbnail
        query = "INSERT INTO storedphoto (filename,type_id,photo_id) VALUES (%s,%s,%s)"
        cursor.execute(query, (thumbnail_online_path, TYPE_THUMBNAIL, photo_id))
        with open(original_store_path, 'rb') as f:
            image_bytes = f.read()
        image_bytes_np = numpy.asarray(image_bytes)
        storefacename=store_base + "_df." + store_ext
        df_online_path = os.path.join(onlinepath, storefacename)
        df_store_path = os.path.join('app/static/user_images', storefacename)
        detect_faces_and_save(image_bytes_np, df_store_path)
        s3.upload_file(storefacename,df_store_path)

        query = "INSERT INTO storedphoto (filename,type_id,photo_id) VALUES (%s,%s,%s)"
        cursor.execute(query, (df_online_path, TYPE_FACE_DETECTED, photo_id))

        cursor.close()

        cnx.commit()

    except Exception as e:
        raise e


@webapp.route('/api/upload', methods=['POST'])
def api_upload():
    if 'file' not in request.files:
        return "No file uploaded"
    session['request'] = session['request'] + 1
    if 'username' not in request.form or 'password' not in request.form:
        return "Authentication error (1)"

    cnx = get_db()
    cursor = cnx.cursor()
    query = "SELECT * FROM user WHERE username = %s"
    cursor.execute(query, (request.form['username'],))
    row = cursor.fetchone()

    if row is None:
        return "Authentication error (2)"

    user_id = row[0]
    hash = row[2]
    salt = row[3]

    password = request.form['password']

    salted_password = "{}{}".format(salt, password)
    m = hashlib.md5()
    m.update(salted_password.encode('utf-8'))
    new_hash = m.digest()

    if new_hash != hash:
        return "Authentication error (3)"

    new_file = request.files['file']

    # if user does not select file, browser also
    # submit a empty part without filename
    if new_file.filename == '':
        return "No file uploaded"

    if is_allowed_file(new_file.filename) == False:
        return "File not allowed"

    try:
        process_file(user_id, new_file)
    except Exception as e:
        return 'Unable to process file: ' + e

    return "OK"


def detect_faces_and_save(image_bytes, file_path):
    imageBytes = numpy.asarray(bytearray(image_bytes), dtype=numpy.uint8)
    image = cv2.imdecode(imageBytes, cv2.IMREAD_UNCHANGED)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
#        flags = cv2.cv.CV_HAAR_SCALE_IMAGE
        flags = cv2.CASCADE_SCALE_IMAGE
    )

    for (x, y, w, h) in faces:
        cv2.rectangle(image, (x, y), (x+w, y+h), (255, 255, 255), 2)

    r, outputImage = cv2.imencode('.jpg', image)
    if False==r:
        raise Exception('Error encoding image')

    with open(file_path, "wb") as f:
        f.write(outputImage)
