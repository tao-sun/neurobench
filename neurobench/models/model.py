from torch import nn
import snntorch as snn
from neurobench.benchmarks.hooks import ActivationHook

from .utils import activation_modules


class NeuroBenchModel:
    """ Abstract class for NeuroBench models. Individual model frameworks are
    responsible for defining model inference.
    """

    def __init__(self, net):
        """ Init using a trained network
        
        Args:
            net: A trained network
        """
        self.activation_modules = activation_modules()
        self.activation_hooks = []
        # for layer in self.activation_layers():
        #     self.activation_hooks.append(ActivationHook(layer))


    def __call__(self, batch):
        """ Includes the whole pipeline from data to inference (output should be same format as targets).

        Args:
            batch: A batch of data to run inference on
        """
        raise NotImplementedError("Subclasses of NeuroBenchModel should implement __call__")

    def __net__(self):
        """ Returns the underlying network
        """
        raise NotImplementedError("Subclasses of NeuroBenchModel should implement __net__")

    def add_activation_module(self, activaton_module):
        """ Add a cutomized activaton_module that can be detected after running the preprocessing pipeline for detecting activation functions
        """
        self.activation_modules.append(activaton_module)

    def activation_layers(self):
        """ Retrieve all the activaton layers of the underlying network
        """
        def check_if_activation(module):
            for activation_module in self.activation_modules:
                if isinstance(module, activation_module):
                    return True

        def get_activation_layers(parent):
            """ Returns all the neuro layers
            """
            layers = []

            children = parent.children()
            for child in children:
                if check_if_activation(child):
                    # is an activation module
                    layers.append(child)
                else:
                    if len(list(child.children())) != 0:
                        # not an activation module and has nested submodules
                        children_layers = get_activation_layers(child)
                        layers.extend(children_layers)
            
            return layers

        
        root = self.__net__()
        layers = get_activation_layers(root)
        return layers

