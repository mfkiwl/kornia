import pytest
import torch.nn as nn

from kornia.metrics import AverageMeter
from kornia.x import EarlyStopping, ModelCheckpoint
from kornia.x.utils import TrainerState


@pytest.fixture
def model():
    return nn.Conv2d(3, 10, kernel_size=1)


def test_callback_modelcheckpoint(tmp_path, model):
    cb = ModelCheckpoint(tmp_path, 'test_monitor')
    assert cb is not None

    metric = {'test_monitor': AverageMeter()}
    metric['test_monitor'].avg = 1.

    cb(model, epoch=0, valid_metric=metric)
    assert cb.best_metric == 1.0
    assert (tmp_path / "model_0.pt").is_file()


def test_callback_earlystopping(model):
    cb = EarlyStopping('test_monitor', patience=2)
    assert cb is not None
    assert cb.counter == 0

    metric = {'test_monitor': AverageMeter()}
    metric['test_monitor'].avg = 1

    state = cb(model, epoch=0, valid_metric=metric)
    assert state == TrainerState.TRAINING
    assert cb.best_score == -1
    assert cb.counter == 0

    metric['test_monitor'].avg = 2
    state = cb(model, epoch=0, valid_metric=metric)
    assert state == TrainerState.TRAINING
    assert cb.best_score == -1
    assert cb.counter == 1

    state = cb(model, epoch=0, valid_metric=metric)
    assert state == TrainerState.TERMINATE
