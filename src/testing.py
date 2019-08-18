import time

import numpy as np
import torch
from selection import CheckModesAndFreezing
from utils import DEVICE, LOGGER


class baseline_tester():
    def __init__(self, never_leave_train_mode):
        self.never_leave_train_mode = never_leave_train_mode
        self.test_time = 0

    def __call__(self, autodl_model, remaining_time):
        '''
        This is called from the model.py and just seperates the
        testing routine from the unchaning code
        '''
        predictions = []

        LOGGER.info('NUM_SEGMENTS: ' + str(autodl_model.model.num_segments))
        LOGGER.info('LR: {0:.4e}'.format(autodl_model.optimizer.param_groups[0]['lr']))
        LOGGER.info('DROPOUT: {0:.4g}'.format(autodl_model.model.dropout))

        with torch.no_grad():
            test_start = time.time()
            if self.never_leave_train_mode:
                CheckModesAndFreezing(autodl_model.model)
            else:
                autodl_model.model.eval()
            autodl_model.test_dl.dataset.reset(
            )  # Just making sure we start at the beginning
            for i, (data, _) in enumerate(autodl_model.test_dl):
                LOGGER.debug('TEST BATCH #' + str(i))
                data = data.to(DEVICE)
                output = autodl_model.model(data)
                predictions += output.cpu().tolist()
                i += 1

        autodl_model.test_time.append(time.time() - test_start)
        return np.array(predictions)