import os
import sys
import math

import numpy as np
from PIL import Image
import scipy.linalg

import chainer
import chainer.cuda
from chainer import Variable
from chainer import serializers
import chainer.functions as F

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.abspath(os.path.dirname(__file__)) + os.path.sep + os.path.pardir)
from common.inception.inception_score import inception_score, Inception


def sample_generate_light(gen, dst, rows=5, cols=5, seed=0):
    @chainer.training.make_extension()
    def make_image(trainer):
        np.random.seed(seed)
        n_images = rows * cols
        xp = gen.xp
        z = Variable(xp.asarray(gen.make_hidden(n_images)))
        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            x = gen(z)
        x = chainer.cuda.to_cpu(x.data)
        np.random.seed()

        x = np.asarray(np.clip(x * 127.5 + 127.5, 0.0, 255.0), dtype=np.uint8)
        _, _, H, W = x.shape
        x = x.reshape((rows, cols, 3, H, W))
        x = x.transpose(0, 3, 1, 4, 2)
        x = x.reshape((rows * H, cols * W, 3))

        preview_dir = '{}/preview'.format(dst)
        preview_path = preview_dir + '/image_latest.png'
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)
        Image.fromarray(x).save(preview_path)

    return make_image


def sample_generate(gen, dst,fix_z=None, rows=10, cols=10, seed=0):
    @chainer.training.make_extension()
    def make_image(trainer):
        np.random.seed(seed)
        n_images = rows * cols
        xp = gen.xp
        if fix_z is not None:
            z = Variable(xp.asarray(fix_z))
        else:
            z = Variable(xp.asarray(gen.make_hidden(n_images)))
        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            x = gen(z)
        x = chainer.cuda.to_cpu(x.data)
        np.random.seed()

        x = np.asarray(np.clip(x * 127.5 + 127.5, 0.0, 255.0), dtype=np.uint8)
        _, _, h, w = x.shape
        x = x.reshape((rows, cols, 3, h, w))
        x = x.transpose(0, 3, 1, 4, 2)
        x = x.reshape((rows * h, cols * w, 3))

        preview_dir = 'result/{}'.format(dst)
        preview_path = preview_dir + '/image{:0>8}.png'.format(trainer.updater.iteration)
        if not os.path.exists(preview_dir):
            os.makedirs(preview_dir)
        Image.fromarray(x).save(preview_path)

    return make_image


def load_inception_model():
    infile = "%s/../common/inception/inception_score.model"%os.path.dirname(__file__)
    model = Inception()
    serializers.load_hdf5(infile, model)
    model.to_gpu()
    return model


def calc_inception(gen, batchsize=100):
    @chainer.training.make_extension()
    def evaluation(trainer):
        model = load_inception_model()

        ims = []
        xp = gen.xp

        n_ims = 50000
        for i in range(0, n_ims, batchsize):
            #print("calc_inception generating: %d"%i)
            z = Variable(xp.asarray(gen.make_hidden(batchsize)))
            with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
                x = gen(z)
            x = chainer.cuda.to_cpu(x.data)
            x = np.asarray(np.clip(x * 127.5 + 127.5, 0.0, 255.0), dtype=np.uint8)
            ims.append(x)
        ims = np.asarray(ims)
        _, _, _, h, w = ims.shape
        ims = ims.reshape((n_ims, 3, h, w)).astype("f")

        mean, _ = inception_score(model, ims)

        if gen.name == 'g':
            chainer.reporter.report({'IS': mean})
        elif gen.name == 'g_ema':
            chainer.reporter.report({'IS_ema': mean})
        elif gen.name == 'g_ma':
            chainer.reporter.report({'IS_ma': mean})
            
    return evaluation


def get_mean_cov(model, ims, batch_size=100):
    n, c, w, h = ims.shape
    n_batches = int(math.ceil(float(n) / float(batch_size)))

    xp = model.xp

    print('Batch size:', batch_size)
    print('Total number of images:', n)
    print('Total number of batches:', n_batches)

    # Compute the softmax predicitions for for all images, split into batches
    # in order to fit in memory

    ys = xp.empty((n, 2048), dtype=xp.float32)  # Softmax container

    for i in range(n_batches):
        #print('Running batch', i + 1, '/', n_batches, '...')
        batch_start = (i * batch_size)
        batch_end = min((i + 1) * batch_size, n)

        ims_batch = ims[batch_start:batch_end]
        ims_batch = xp.asarray(ims_batch)  # To GPU if using CuPy
        ims_batch = Variable(ims_batch)

        # Resize image to the shape expected by the inception module
        if (w, h) != (299, 299):
            ims_batch = F.resize_images(ims_batch, (299, 299))  # bilinear

        # Feed images to the inception module to get the softmax predictions
        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            y = model(ims_batch, get_feature=True)
        ys[batch_start:batch_end] = y.data

    mean = xp.mean(ys, axis=0).get()
    # cov = F.cross_covariance(ys, ys, reduce="no").data.get()
    cov = np.cov(ys.get().T)

    return mean, cov

def FID(m0,c0,m1,c1):
    ret = 0
    ret += np.sum((m0-m1)**2)
    ret += np.trace(c0 + c1 - 2.0*scipy.linalg.sqrtm(np.dot(c0, c1)))
    return np.real(ret)

def calc_FID(gen, dataset='cifar10',size=32, batchsize=100):
    """Frechet Inception Distance proposed by https://arxiv.org/abs/1706.08500"""
    @chainer.training.make_extension()
    def evaluation(trainer):
        if dataset == 'cifar10':
            stat_file="%s/../common/cifar-10-fid.npz"%os.path.dirname(__file__)
        elif dataset == 'stl10' and size == 32:
            stat_file="%s/../common/stl-10-32-fid.npz"%os.path.dirname(__file__)
        elif dataset == 'stl10' and size == 48:
            stat_file="%s/../common/stl-10-48-fid.npz"%os.path.dirname(__file__)
        elif dataset == 'stl10' and size == 64:
            stat_file="%s/../common/stl-10-64-fid.npz"%os.path.dirname(__file__)
        elif dataset == 'imagenet':
            stat_file="%s/../common/fid_stats_imagenet_train_mine.npz"%os.path.dirname(__file__)
        elif dataset == 'celeba' and size == 64:
            stat_file="%s/../common/fid_stats_celeba_crop_64.npz"%os.path.dirname(__file__)
        elif dataset == 'celeba' and size == 128:
            stat_file="%s/../common/fid_stats_celeba_crop_128.npz"%os.path.dirname(__file__)
        else:
            NotImplementedError('no such dataset')
        model = load_inception_model()
        stat = np.load(stat_file)
        
        n_ims = 10000
        xp = gen.xp
        xs = []
        for i in range(0, n_ims, batchsize):
            z = Variable(xp.asarray(gen.make_hidden(batchsize)))
            with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
                x = gen(z)
            x = chainer.cuda.to_cpu(x.data)
            x = np.asarray(np.clip(x * 127.5 + 127.5, 0.0, 255.0), dtype="f")
            xs.append(x)
        xs = np.asarray(xs)
        _, _, _, h, w = xs.shape

        with chainer.using_config('train', False), chainer.using_config('enable_backprop', False):
            mean, cov = get_mean_cov(model, np.asarray(xs).reshape((-1, 3, h, w)))
        #fid = FID(stat["mean"], stat["cov"], mean, cov)
        fid = FID(stat["mean"], stat["cov"], mean, cov)
        if gen.name == 'g':
            chainer.reporter.report({'FID': fid})
        elif gen.name == 'g_ema':
            chainer.reporter.report({'FID_ema': fid})
        elif gen.name == 'g_ma':
            chainer.reporter.report({'FID_ma': fid})

    return evaluation