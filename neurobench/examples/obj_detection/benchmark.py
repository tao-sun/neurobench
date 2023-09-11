import torch

from neurobench.datasets import Gen4DetectionDataLoader
from neurobench.models import NeuroBenchModel
from neurobench.benchmarks import Benchmark

from obj_det_model import Vanilla, Vanilla_lif

from metavision_ml.detection.anchors import Anchors
from metavision_ml.detection.rpn import BoxHead

# dataloader itself takes about 7 minutes for loading, with model evaluation and score calculation is about 20 minutes on i9-12900KF, RTX3080
test_set_dataloader = Gen4DetectionDataLoader(dataset_path="data/Gen 4 Multi channel",
        split="testing",
        label_map_path="neurobench/datasets/label_map_dictionary.json",
        batch_size = 12,
        num_tbins = 12,
        preprocess_function_name="multi_channel_timesurface",
        delta_t=50000,
        channels=6,  # multichannel six channels
        height=360,
        width=640,
        max_incr_per_pixel=5,
        class_selection=["pedestrian", "two wheeler", "car"],
        num_workers=2)

# Evaluation pipeline written and models trained by Shenqi Wang (wang69@imec.be) and Guangzhi Tang (guangzhi.tang@imec.nl) at imec.

class ObjDetectionModel(NeuroBenchModel):
    def __init__(self, net, box_coder, head):
        self.net = net
        self.box_coder = box_coder
        self.head = head

    def __call__(self, batch):
        self.net.eval()
        inputs = batch.permute(1, 0, 2, 3, 4).to(device='cuda') # dataloader supplies batch,timestep,*; model expects timestep,batch,*
        with torch.no_grad():
            feature = self.net(inputs)
            loc_preds_val, cls_preds_val = self.head(feature)
            scores = self.head.get_scores(cls_preds_val)
            scores = scores.to('cpu')
            for i, feat in enumerate(feature):
                feature[i] = feature[i].to('cpu')
            inputs = inputs.to('cpu')
            loc_preds_val = loc_preds_val.to('cpu')
            preds = box_coder.decode(feature, inputs, loc_preds_val, scores, batch_size=inputs.shape[1], score_thresh=0.05,
                        nms_thresh=0.5, max_boxes_per_input=500)
        return preds

    def __net__(self):
        # returns only network, not box_coder and head
        return self.net

# Loading the model
mode = "hybrid" # "ann" or "hybrid
if mode == "ann":
    # baseline ANN RED architecture
    model = Vanilla(cin = 6, cout = 256, base = 16)
    box_coder = Anchors(num_levels=model.levels, anchor_list="PSEE_ANCHORS", variances=[0.1, 0.2])
    head = BoxHead(model.cout, box_coder.num_anchors, 3+1, 0)
    model = model.to('cuda')
    head = head.to('cuda')
    model.load_state_dict(torch.load('neurobench/examples/obj_detection/model_data/save_models/25_ann_model.pth',map_location=torch.device('cuda')))
    head.load_state_dict(torch.load('neurobench/examples/obj_detection/model_data/save_models/25_ann_pd.pth',map_location=torch.device('cuda')))
elif mode == "hybrid":
    # hybrid SNN of above architecture
    model = Vanilla_lif(cin = 6, cout = 256, base = 16)
    box_coder = Anchors(num_levels=model.levels, anchor_list="PSEE_ANCHORS", variances=[0.1, 0.2])
    head = BoxHead(model.cout, box_coder.num_anchors, 3+1, 0)
    model = model.to('cuda')
    head = head.to('cuda')
    model.load_state_dict(torch.load('neurobench/examples/obj_detection/model_data/save_models/14_hybrid_model.pth',map_location=torch.device('cuda')))
    head.load_state_dict(torch.load('neurobench/examples/obj_detection/model_data/save_models/14_hybrid_pd.pth',map_location=torch.device('cuda')))
else:
    raise ValueError("mode must be ann or hybrid")

model = ObjDetectionModel(model, box_coder, head)

# Evaluation

preprocessors = []
postprocessors = []

'''
TODO:
Currently seems to be a bug in connection sparsity where the iteration
isn't fine grained enough to examine the conv2d layers (iterates over
modules composed of many layers)

static_metrics = ["model_size", "connection_sparsity"]

'''

static_metrics = ["model_size"]
data_metrics = ["COCO_mAP"]

benchmark = Benchmark(model, test_set_dataloader, preprocessors, postprocessors, [static_metrics, data_metrics])
results = benchmark.run()
print(results)

# batch size of inference slightly affects the results.

# Results - ANN, batch = 12
# {'model_size': 91314912, 'COCO_mAP': 0.43047329135339685}
# Results - Hybrid, batch = 12
# {'model_size': 12133872, 'COCO_mAP': 0.2711162430904825}