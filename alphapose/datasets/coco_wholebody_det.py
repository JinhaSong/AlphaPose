# -----------------------------------------------------
# Copyright (c) Shanghai Jiao Tong University. All rights reserved.
# Written by Haoyi Zhu
# -----------------------------------------------------

"""Coco WholeBody Human Detection Box dataset."""
import json
import os

import cv2
import torch
import torch.utils.data as data
from tqdm import tqdm

from lib.pose.alphapose.alphapose.utils.presets import SimpleTransform
from alphapose.detector.apis import get_detector
from lib.pose.alphapose.alphapose.models.builder import DATASET


@DATASET.register_module
class coco_wholebody_det(data.Dataset):
    """ Coco WholeBody human detection box dataset.

    """
    EVAL_JOINTS = list(range(133))

    def __init__(self,
                 det_file=None,
                 opt=None,
                 **cfg):

        self._cfg = cfg
        self._opt = opt
        self._preset_cfg = cfg['PRESET']
        self._root = cfg['ROOT']
        self._img_prefix = cfg['IMG_PREFIX']
        if not det_file:
            det_file = cfg['DET_FILE']
        self._ann_file = os.path.join(self._root, cfg['ANN'])

        if os.path.exists(det_file):
            print("Detection results exist, will use it")
        else:
            print("Will create detection results to {}".format(det_file))
            self.write_coco_json(det_file)

        assert os.path.exists(det_file), "Error: no detection results found"
        with open(det_file, 'r') as fid:
            self._det_json = json.load(fid)

        self._input_size = self._preset_cfg['IMAGE_SIZE']
        self._output_size = self._preset_cfg['HEATMAP_SIZE']

        self._sigma = self._preset_cfg['SIGMA']

        if self._preset_cfg['TYPE'] == 'simple':
            self.transformation = SimpleTransform(
                self, scale_factor=0,
                input_size=self._input_size,
                output_size=self._output_size,
                rot=0, sigma=self._sigma,
                train=False, add_dpg=False)

    def __getitem__(self, index):
        det_res = self._det_json[index]
        if not isinstance(det_res['image_id'], int):
            img_id, _ = os.path.splitext(os.path.basename(det_res['image_id']))
            img_id = int(img_id)
        else:
            img_id = det_res['image_id']
        img_path = os.path.join(self._root, self._img_prefix, '%012d.jpg' % img_id)

        # Load image
        image = cv2.cvtColor(cv2.imread(img_path), cv2.COLOR_BGR2RGB) # scipy.misc.imread(img_path, mode='RGB') is deprecated

        imght, imgwidth = image.shape[1], image.shape[2]
        x1, y1, w, h = det_res['bbox']
        bbox = [x1, y1, x1 + w, y1 + h]
        inp, bbox = self.transformation.test_transform(image, bbox)
        return inp, torch.Tensor(bbox), torch.Tensor([det_res['bbox']]), torch.Tensor([det_res['image_id']]), torch.Tensor([det_res['score']]), torch.Tensor([imght]), torch.Tensor([imgwidth])

    def __len__(self):
        return len(self._det_json)

    def write_coco_json(self, det_file):
        from pycocotools.coco import COCO
        import pathlib

        _coco = COCO(self._ann_file)
        image_ids = sorted(_coco.getImgIds())
        det_model = get_detector(self._opt)
        dets = []
        for entry in tqdm(_coco.loadImgs(image_ids)):
            abs_path = os.path.join(
                self._root, self._img_prefix, entry['file_name'])
            det = det_model.detect_one_img(abs_path)
            if det:
                dets += det
        pathlib.Path(os.path.split(det_file)[0]).mkdir(parents=True, exist_ok=True)
        json.dump(dets, open(det_file, 'w'))

    @property
    def joint_pairs(self):
        """Joint pairs which defines the pairs of joint to be swapped
        when the image is flipped horizontally."""
        return [[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12], [13, 14], [15, 16], 
                [17, 20], [18, 21], [19, 22], [23, 39], [24, 38], [25, 37], [26, 36], 
                [27, 35], [28, 34], [29, 33], [30, 32], [40, 49], [41, 48], [42, 47], 
                [43, 46], [44, 45], [59, 68], [60, 67], [61, 66], [62, 65], [63, 70], 
                [64, 69], [54, 58], [55, 57], [71, 77], [72, 76], [73, 75], [84, 86], 
                [90, 88], [83, 87], [82, 78], [81, 79], [91, 112], [92, 113], [93, 114], 
                [94, 115], [95, 116], [96, 117], [97, 118], [98, 119], [99, 120], 
                [100, 121], [101, 122], [102, 123], [103, 124], [104, 125], [105, 126], 
                [106, 127], [107, 128], [108, 129], [109, 130], [110, 131], [111, 132]]
