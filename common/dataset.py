import os

import numpy as np
from PIL import Image
import chainer
from chainer.dataset import dataset_mixin
from glob import glob


class Cifar10Dataset(dataset_mixin.DatasetMixin):
    def __init__(self, test=False):
        d_train, d_test = chainer.datasets.get_cifar10(ndim=3, withlabel=False, scale=1.0)
        if test:
            self.ims = d_test
        else:
            self.ims = d_train
        self.ims = self.ims * 2 - 1.0  # [-1.0, 1.0]
        print("load cifar-10.  shape: ", self.ims.shape)

    def __len__(self):
        return self.ims.shape[0]

    def get_example(self, i):
        return self.ims[i]


def image_to_np(img):
    img = img.convert('RGB')
    img = np.asarray(img, dtype=np.uint8)
    img = img.transpose((2, 0, 1)).astype("f")
    if img.shape[0] == 1:
        img = np.broadcast_to(img, (3, img.shape[1], img.shape[2]))
    img = (img - 127.5)/127.5
    return img

'''
def preprocess_image(img, crop_width=256, img2np=True):
    wid = min(img.size[0], img.size[1])
    ratio = crop_width / (wid + 1e-4)
    img = img.resize((int(ratio * img.size[0]), int(ratio * img.size[1])), Image.BILINEAR)
    x_l = (img.size[0]) // 2 - crop_width // 2
    x_r = x_l + crop_width
    y_u = 0
    y_d = y_u + crop_width
    img = img.crop((x_l, y_u, x_r, y_d))

    if img2np:
        img = image_to_np(img)
    return img
'''
def preprocess_image(img, resize=128, img2np=True):
    h,w = img.size[0], img.size[1]
    wid = min(h, w)
    x_l = int((h-wid)/2.0)
    x_r = x_l + wid
    y_u = int((w-wid)/2.0)
    y_d = y_u + wid
    img = img.crop((x_l, y_u, x_r, y_d))
    img = img.resize((resize, resize), Image.BILINEAR)

    if img2np:
        img = image_to_np(img)
    return img

def preprocess_image_no_crop(img, resize=64, img2np=True):
    wid = min(img.size[0], img.size[1])
    ratio = 1.0*resize / wid
    img = img.resize((int(ratio * img.size[0]), int(ratio * img.size[1])), Image.BILINEAR)

    if img2np:
        img = image_to_np(img)
    return img


def find_all_files(directory):
    """http://qiita.com/suin/items/cdef17e447ceeff6e79d"""
    for root, dirs, files in os.walk(directory):
        yield root
        for file in files:
            yield os.path.join(root, file)


class CelebADataset(dataset_mixin.DatasetMixin):
    def __init__(self, resize=128):
        self.resize = resize
        self.image_files = glob('/home/yasin/sharedLocal/data/celeba/img_align_celeba/*.jpg')
        print(len(self.image_files))

    def __len__(self):
        return len(self.image_files)

    def get_example(self, i):
        np.random.seed()
        img = None

        while img is None:
            try:
                fn = "%s" % (self.image_files[i])
                img = Image.open(fn)
            except Exception as e:
                print(i, fn, str(e))
        return preprocess_image(img, resize=self.resize)
    
class ImagenetDataset(dataset_mixin.DatasetMixin):
    def __init__(self, file_list, crop_width=256):
        self.crop_width = crop_width
        self.image_files = file_list
        print(len(self.image_files))

    def __len__(self):
        return len(self.image_files)

    def get_example(self, i):
        np.random.seed()
        img = None

        while img is None:
            # print(i,id)
            try:
                fn = "%s" % (self.image_files[i])
                img = Image.open(fn)
            except Exception as e:
                print(i, fn, str(e))
        return preprocess_image(img, crop_width=self.crop_width)
    
class Imagenet64Dataset(dataset_mixin.DatasetMixin):
    def __init__(self):
        self.image_files = glob('/home/yasin/sharedLocal/train_64x64/*.png')
        print(len(self.image_files))

    def __len__(self):
        return len(self.image_files)

    def get_example(self, i):
        np.random.seed()
        img = None

        while img is None:
            # print(i,id)
            try:
                fn = "%s" % (self.image_files[i])
                img = Image.open(fn)
            except Exception as e:
                print(i, fn, str(e))
        return image_to_np(img)
    
class Imagenet32Dataset(dataset_mixin.DatasetMixin):
    def __init__(self):
        self.image_files = glob('/home/users/ntu/yasin001/project/train_32x32/*.png')
        print(len(self.image_files))

    def __len__(self):
        return len(self.image_files)

    def get_example(self, i):
        np.random.seed()
        img = None

        while img is None:
            # print(i,id)
            try:
                fn = "%s" % (self.image_files[i])
                img = Image.open(fn)
            except Exception as e:
                print(i, fn, str(e))
        return image_to_np(img)
    
class Stl10Dataset(dataset_mixin.DatasetMixin):
    def __init__(self, resize=64):
        self.resize = resize
        self.image_files = glob('/home/users/ntu/yasin001/project/stl10/*.jpg')
        print(len(self.image_files))

    def __len__(self):
        return len(self.image_files)

    def get_example(self, i):
        np.random.seed()
        img = None

        while img is None:
            # print(i,id)
            try:
                fn = "%s" % (self.image_files[i])
                img = Image.open(fn)
            except Exception as e:
                print(i, fn, str(e))
        return preprocess_image_no_crop(img, resize=self.resize)
    
class Stl10_48_Dataset(dataset_mixin.DatasetMixin):
    def __init__(self):
        self.image_files = glob('/home/yasin/sharedLocal/data/stl10-48/*.jpg')
        print(len(self.image_files))

    def __len__(self):
        return len(self.image_files)

    def get_example(self, i):
        np.random.seed()
        img = None

        while img is None:
            # print(i,id)
            try:
                fn = "%s" % (self.image_files[i])
                img = Image.open(fn)
            except Exception as e:
                print(i, fn, str(e))
        return image_to_np(img)
