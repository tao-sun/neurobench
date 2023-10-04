import torch
from torch.utils.data import DataLoader, Subset

from neurobench.datasets import PrimateReaching
# from neurobench.models.snntorch_models import SNNTorchModel
from neurobench.benchmarks import Benchmark
from neurobench.examples.primate_reaching.SNN2 import SNN2

from neurobench.models import TorchModel
import snntorch as snn

# Download data to /data/primate_reaching/PrimateReachingDataset. See PrimateReaching
# class for download instructions.

# The dataloader and preprocessor has been combined together into a single class
files = ["indy_20160622_01", "indy_20160630_01", "indy_20170131_02",
            "loco_20170210_03", "loco_20170217_02", "loco_20170301_05"]

footprint = []
connection_sparsity = []
activation_sparsity = []
macs = []
acs = []
r2 = []


for filename in files:
    print("Processing {}".format(filename))
    dataset = PrimateReaching(file_path="data/primate_reaching/PrimateReachingDataset/", filename=filename,
                              num_steps=50, train_ratio=0.5, bin_width=0.004,
                              biological_delay=0, split_num=1, remove_segments_inactive=True)
    test_set_loader = DataLoader(Subset(dataset, dataset.ind_test), batch_size=len(dataset.ind_test), shuffle=False)

    net = SNN2(input_size=dataset.input_feature_size)
    net.load_state_dict(torch.load("neurobench/examples/primate_reaching/model_data/SNN2_{}.pt".format(filename), map_location=torch.device('cpu'))
                        ['model_state_dict'], strict=False)

    # init the model
    net.reset()
    model = TorchModel(net) # using TorchModel instead of SNNTorchModel because the SNN iterates over dimension 0
    model.add_activation_module(snn.SpikingNeuron)

    static_metrics = ["model_size", "connection_sparsity"]
    data_metrics = ["r2", "activation_sparsity"]

    # Benchmark expects the following:
    benchmark = Benchmark(model, test_set_loader, [], [], [static_metrics, data_metrics])
    results = benchmark.run()
    print(results)

    footprint.append(results['model_size'])
    connection_sparsity.append(results['connection_sparsity'])
    activation_sparsity.append(results['activation_sparsity'])
    macs.append(results['synaptic_operations']['MACs'])
    acs.append(results['synaptic_operations']['ACs'])
    r2.append(results['r2'])

print("Footprint: {}".format(footprint))
print("Connection sparsity: {}".format(connection_sparsity))
print("Activation sparsity: {}".format(activation_sparsity))
print("MACs: {}".format(macs))
print("ACs: {}".format(acs))
print("R2: {}".format(r2))
