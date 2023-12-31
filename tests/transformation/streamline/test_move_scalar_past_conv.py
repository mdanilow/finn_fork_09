# Copyright (c) 2020, Xilinx
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of FINN nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import pytest

import numpy as np
import onnx.helper as oh
from onnx import TensorProto
from qonnx.core.modelwrapper import ModelWrapper
from qonnx.transformation.infer_shapes import InferShapes
from qonnx.util.basic import qonnx_make_model

import finn.core.onnx_exec as ox
from finn.transformation.streamline import MoveAddPastConv, MoveScalarMulPastConv


@pytest.mark.streamline
@pytest.mark.parametrize("padding", [False, True])
@pytest.mark.parametrize(
    "test_args",
    [("Add", MoveAddPastConv()), ("Mul", MoveScalarMulPastConv())],
)
def test_move_scalar_past_conv(test_args, padding):
    scalar_op = test_args[0]
    transf_fxn = test_args[1]

    in_feature_dim = 7
    in_chn = 3

    stages = 2
    kernel_size = 3

    out_feature_dim = (
        in_feature_dim if padding else in_feature_dim - (kernel_size // 2 * 2) * stages
    )

    input_shape = [1, in_chn, in_feature_dim, in_feature_dim]
    output_shape = [1, in_chn, out_feature_dim, out_feature_dim]

    conv_param_shape = [in_chn, in_chn, kernel_size, kernel_size]

    conv_config = {}
    conv_config["dilations"] = [1, 1]
    conv_config["group"] = 1
    conv_config["kernel_shape"] = [kernel_size, kernel_size]
    if padding:
        conv_config["pads"] = [1, 1, 1, 1]
    else:
        conv_config["pads"] = [0, 0, 0, 0]
    conv_config["strides"] = [1, 1]

    top_in = oh.make_tensor_value_info("top_in", TensorProto.FLOAT, input_shape)
    top_out = oh.make_tensor_value_info("top_out", TensorProto.FLOAT, output_shape)

    value_info = [oh.make_tensor_value_info("p1", TensorProto.FLOAT, [1])]
    value_info += [oh.make_tensor_value_info("p2", TensorProto.FLOAT, conv_param_shape)]
    value_info += [oh.make_tensor_value_info("p3", TensorProto.FLOAT, conv_param_shape)]

    modelproto = qonnx_make_model(
        oh.make_graph(
            name="test",
            inputs=[top_in],
            outputs=[top_out],
            value_info=value_info,
            nodes=[
                oh.make_node(scalar_op, ["top_in", "p1"], ["t1"]),
                oh.make_node("Conv", ["t1", "p2"], ["t2"], **conv_config),
                oh.make_node("Conv", ["t2", "p3"], ["top_out"], **conv_config),
            ],
        )
    )
    model = ModelWrapper(modelproto)
    model = model.transform(InferShapes())

    np.random.seed(0)
    model.set_initializer("p1", *np.random.rand(1).astype(np.float32))
    model.set_initializer("p2", np.random.rand(*conv_param_shape).astype(np.float32))
    model.set_initializer("p3", np.random.rand(*conv_param_shape).astype(np.float32))
    new_model = model.transform(transf_fxn)
    inp_dict = {"top_in": np.random.rand(*input_shape).astype(np.float32)}

    assert ox.compare_execution(model, new_model, inp_dict)
    if scalar_op == "Add":
        if padding:
            assert new_model.graph.node[0].op_type == scalar_op
            assert new_model.graph.node[1].op_type == "Conv"
            assert new_model.graph.node[2].op_type == "Conv"
        else:
            assert new_model.graph.node[0].op_type == "Conv"
            assert new_model.graph.node[1].op_type == "Conv"
            assert new_model.graph.node[2].op_type == scalar_op
    else:
        assert new_model.graph.node[0].op_type == "Conv"
        assert new_model.graph.node[1].op_type == "Conv"
        assert new_model.graph.node[2].op_type == scalar_op


@pytest.mark.streamline
@pytest.mark.parametrize(
    "test_args",
    [("Add", MoveAddPastConv()), ("Mul", MoveScalarMulPastConv())],
)
def test_move_scalar_past_conv_only_if_linear(test_args):
    scalar_op = test_args[0]
    transf_fxn = test_args[1]

    in_feature_dim = 7
    in_chn = 1
    padding = False
    stages = 3
    kernel_size = 3

    out_feature_dim = (
        in_feature_dim if padding else in_feature_dim - (kernel_size // 2 * 2) * stages
    )

    input_shape = [1, in_chn, in_feature_dim, in_feature_dim]
    output_shape = [1, in_chn, out_feature_dim, out_feature_dim]

    conv_param_shape = [in_chn, in_chn, kernel_size, kernel_size]

    conv_config = {}
    conv_config["dilations"] = [1, 1]
    conv_config["group"] = 1
    conv_config["kernel_shape"] = [kernel_size, kernel_size]
    conv_config["pads"] = [0, 0, 0, 0]
    conv_config["strides"] = [1, 1]

    top_in = oh.make_tensor_value_info("top_in", TensorProto.FLOAT, input_shape)
    top_out = oh.make_tensor_value_info("top_out", TensorProto.FLOAT, output_shape)

    value_info = [oh.make_tensor_value_info("p1", TensorProto.FLOAT, [1])]
    value_info += [oh.make_tensor_value_info("p2", TensorProto.FLOAT, conv_param_shape)]
    value_info += [oh.make_tensor_value_info("p3", TensorProto.FLOAT, conv_param_shape)]
    value_info += [oh.make_tensor_value_info("p4", TensorProto.FLOAT, conv_param_shape)]
    value_info += [oh.make_tensor_value_info("p5", TensorProto.FLOAT, conv_param_shape)]

    modelproto = qonnx_make_model(
        oh.make_graph(
            name="test",
            inputs=[top_in],
            outputs=[top_out],
            value_info=value_info,
            nodes=[
                oh.make_node("Conv", ["top_in", "p2"], ["t1"], **conv_config),
                oh.make_node(scalar_op, ["t1", "p1"], ["t2"]),
                oh.make_node("Conv", ["t2", "p3"], ["t3"], **conv_config),
                oh.make_node("Conv", ["t2", "p4"], ["t4"], **conv_config),
                oh.make_node(scalar_op, ["t3", "t4"], ["t5"]),
                oh.make_node("Conv", ["t5", "p5"], ["top_out"], **conv_config),
            ],
        )
    )
    model = ModelWrapper(modelproto)
    model = model.transform(InferShapes())

    np.random.seed(0)
    model.set_initializer("p1", *np.random.rand(1).astype(np.float32))
    model.set_initializer("p2", np.random.rand(*conv_param_shape).astype(np.float32))
    model.set_initializer("p3", np.random.rand(*conv_param_shape).astype(np.float32))
    model.set_initializer("p4", np.random.rand(*conv_param_shape).astype(np.float32))
    model.set_initializer("p5", np.random.rand(*conv_param_shape).astype(np.float32))
    new_model = model.transform(transf_fxn)
    inp_dict = {"top_in": np.random.rand(*input_shape).astype(np.float32)}

    assert ox.compare_execution(model, new_model, inp_dict)
    assert new_model.graph.node[0].op_type == "Conv"
    assert new_model.graph.node[1].op_type == scalar_op
    assert new_model.graph.node[2].op_type == "Conv"
    assert new_model.graph.node[3].op_type == "Conv"
    assert new_model.graph.node[4].op_type == scalar_op
    assert new_model.graph.node[5].op_type == "Conv"
