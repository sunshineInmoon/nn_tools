from __future__ import absolute_import
import torch
import torch.nn as nn
import numpy as np
from torch.autograd import Variable
from collections import OrderedDict
from .layers import *
from . import save_csv
from .utils import print_by_layers

tracked_layers=[]
blob_dict=[]
layer_name_dict={}

def _analyse(module,raw_input):
    input=[]
    for i in raw_input: #raw_input通常是一个元组
        if isinstance(i,torch.Tensor):
            s = i.size()
            input.append(Blob(s))
    out=None
    name=layer_name_dict[module] #layer_name_dict 在前面就已经填充好
    if isinstance(module,nn.Conv2d):
        out=Conv(input[0],module.kernel_size,module.out_channels,
                 module.stride,module.padding,group_size=module.groups,name=name)
    elif isinstance(module,nn.ConvTranspose2d):
        out=Conv(input[0],module.kernel_size,module.out_channels,
                 module.stride,module.padding,group_size=module.groups,name=name,transpose=True)
    elif isinstance(module,nn.BatchNorm2d):
        out=Norm(input[0],'batch_norm',name=name)
    elif isinstance(module,nn.Linear):
        out=fc(input[0],module.out_features,name=name)
    elif isinstance(module,nn.MaxPool2d):
        out = pool(input[0], module.kernel_size,module.stride,module.padding,
                   name=name,pool_type='max')
    elif isinstance(module,nn.AvgPool2d):
        out = pool(input[0], module.kernel_size,module.stride,module.padding,
                   name=name,pool_type='avg')
    elif isinstance(module,nn.ReLU):
        out = Activation(input[0],'relu',name=name)
    elif isinstance(module,nn.Conv3d):
        out=Conv(input[0],module.kernel_size,module.out_channels,
                 module.stride,module.padding,group_size=module.groups,name=name)

    if out:
        tracked_layers.append(out)
    else:
        print('WARNING: skip Module {}' .format(module))

def module_hook(module, input, output):
    # print('module hook')
    # print module
    # for i in input:
    #     print ('input',i.size())
    # for i in output:
    #     print('out', i.size())
    _analyse(module,input)

def register(module):
    module.register_forward_hook(module_hook)

def analyse(net, inputs):
    """
    analyse the network given input
    :param net: torch.nn.Module
    :param inputs: torch.Variable, torch.Tensor or list of them
    :return: blob_dict, tracked_layers
    """
    del tracked_layers[:]# 清空列表
    del blob_dict[:]
    if not isinstance(inputs,(list,tuple)):# 将输入的Tensor放到一个list中
        raw_inputs=[inputs]
    else:
        raw_inputs=inputs
    _inputs=[]
    for name,layer in net.named_modules():# 从整体到局部遍历整个模型中模块和层
        layer_name_dict[layer]=name# key居然是具体的模块和层，而不是对应的名字
    for i in raw_inputs: #遍历输入
        if isinstance(i,Variable):
            _inputs.append(i)
        elif isinstance(i,torch.Tensor):# 输入一般为一个Tensor
            _inputs.append(Variable(i))
        elif isinstance(i,np.ndarray):
            _inputs.append(Variable(torch.Tensor(i)))
        else:
            raise NotImplementedError("Not Support the input type {}".format(type(i)))
    net.apply(register)
    net.forward(*_inputs)
    for _,m in net.named_modules():
        m._forward_hooks.clear()
    print_by_layers(tracked_layers)
    return blob_dict,tracked_layers

def profilling(net,input):
    """ Old API of analyse """
    return analyse(net,input)