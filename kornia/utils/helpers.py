import warnings
from typing import Any, List, Optional, Tuple

import torch

from kornia.utils._compat import solve


def _pytorch_version_geq(major, minor):
    version = torch.__version__.split('.')
    return (int(version[0]) >= major) and (int(version[1]) >= minor)


def _extract_device_dtype(tensor_list: List[Optional[Any]]) -> Tuple[torch.device, torch.dtype]:
    """Check if all the input are in the same device (only if when they are torch.Tensor).

    If so, it would return a tuple of (device, dtype). Default: (cpu, ``get_default_dtype()``).

    Returns:
        [torch.device, torch.dtype]
    """
    device, dtype = None, None
    for tensor in tensor_list:
        if tensor is not None:
            if not isinstance(tensor, (torch.Tensor,)):
                continue
            _device = tensor.device
            _dtype = tensor.dtype
            if device is None and dtype is None:
                device = _device
                dtype = _dtype
            elif device != _device or dtype != _dtype:
                raise ValueError(
                    "Passed values are not in the same device and dtype."
                    f"Got ({device}, {dtype}) and ({_device}, {_dtype})."
                )
    if device is None:
        # TODO: update this when having torch.get_default_device()
        device = torch.device('cpu')
    if dtype is None:
        dtype = torch.get_default_dtype()
    return (device, dtype)


def _torch_inverse_cast(input: torch.Tensor) -> torch.Tensor:
    """Helper function to make torch.inverse work with other than fp32/64.

    The function torch.inverse is only implemented for fp32/64 which makes impossible to be used by fp16 or others. What
    this function does, is cast input data type to fp32, apply torch.inverse, and cast back to the input dtype.
    """
    if not isinstance(input, torch.Tensor):
        raise AssertionError(f"Input must be torch.Tensor. Got: {type(input)}.")
    dtype: torch.dtype = input.dtype
    if dtype not in (torch.float32, torch.float64):
        dtype = torch.float32
    return torch.inverse(input.to(dtype)).to(input.dtype)


def _torch_histc_cast(input: torch.Tensor, bins: int, min: int, max: int) -> torch.Tensor:
    """Helper function to make torch.histc work with other than fp32/64.

    The function torch.histc is only implemented for fp32/64 which makes impossible to be used by fp16 or others. What
    this function does, is cast input data type to fp32, apply torch.inverse, and cast back to the input dtype.
    """
    if not isinstance(input, torch.Tensor):
        raise AssertionError(f"Input must be torch.Tensor. Got: {type(input)}.")
    dtype: torch.dtype = input.dtype
    if dtype not in (torch.float32, torch.float64):
        dtype = torch.float32
    return torch.histc(input.to(dtype), bins, min, max).to(input.dtype)


def _torch_svd_cast(input: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Helper function to make torch.svd work with other than fp32/64.

    The function torch.svd is only implemented for fp32/64 which makes
    impossible to be used by fp16 or others. What this function does, is cast
    input data type to fp32, apply torch.svd, and cast back to the input dtype.

    NOTE: in torch 1.8.1 this function is recommended to use as torch.linalg.svd
    """
    if not isinstance(input, torch.Tensor):
        raise AssertionError(f"Input must be torch.Tensor. Got: {type(input)}.")
    dtype: torch.dtype = input.dtype
    if dtype not in (torch.float32, torch.float64):
        dtype = torch.float32

    out1, out2, out3 = torch.svd(input.to(dtype))

    return (out1.to(input.dtype), out2.to(input.dtype), out3.to(input.dtype))


# TODO: return only `torch.Tensor` and review all the calls to adjust
def _torch_solve_cast(input: torch.Tensor, A: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    """Helper function to make torch.solve work with other than fp32/64.

    The function torch.solve is only implemented for fp32/64 which makes impossible to be used by fp16 or others. What
    this function does, is cast input data type to fp32, apply torch.svd, and cast back to the input dtype.
    """
    if not isinstance(input, torch.Tensor):
        raise AssertionError(f"Input must be torch.Tensor. Got: {type(input)}.")
    dtype: torch.dtype = input.dtype
    if dtype not in (torch.float32, torch.float64):
        dtype = torch.float32

    out = solve(A.to(dtype), input.to(dtype))

    return (out.to(input.dtype), out)


def safe_solve_with_mask(B: torch.Tensor, A: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    r"""Helper function, which avoids crashing because of singular matrix input and outputs the
    mask of valid solution"""
    if not (_pytorch_version_geq(1, 10)):
        sol, lu = _torch_solve_cast(B, A)
        warnings.warn('PyTorch version < 1.10, solve validness mask maybe not correct', RuntimeWarning)
        return sol, lu, torch.ones(len(A), dtype=torch.bool, device=A.device)
    # Based on https://github.com/pytorch/pytorch/issues/31546#issuecomment-694135622
    if not isinstance(B, torch.Tensor):
        raise AssertionError(f"B must be torch.Tensor. Got: {type(B)}.")
    dtype: torch.dtype = B.dtype
    if dtype not in (torch.float32, torch.float64):
        dtype = torch.float32
    A_LU, pivots, info = torch.lu(A.to(dtype), get_infos=True)
    valid_mask: torch.Tensor = info == 0
    A_LU_solvable = A_LU[valid_mask]
    X = torch.lu_solve(B.to(dtype), A_LU, pivots)
    A_LU_out = A_LU
    return X.to(B.dtype), A_LU.to(A.dtype), valid_mask


def safe_inverse_with_mask(A: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
    r"""Helper function, which avoids crashing because of non-invertable matrix input and outputs the
    mask of valid solution"""
    # Based on https://github.com/pytorch/pytorch/issues/31546#issuecomment-694135622
    if not (_pytorch_version_geq(1, 9)):
        inv = _torch_inverse_cast(A)
        warnings.warn('PyTorch version < 1.9, inverse validness mask maybe not correct', RuntimeWarning)
        return inv, torch.ones(len(A), dtype=torch.bool, device=A.device)
    if not isinstance(A, torch.Tensor):
        raise AssertionError(f"A must be torch.Tensor. Got: {type(A)}.")
    dtype_original: torch.dtype = A.dtype
    if dtype_original not in (torch.float32, torch.float64):
        dtype = torch.float32
    else:
        dtype = dtype_original
    from torch.linalg import inv_ex
    inverse, info = inv_ex(A.to(dtype))
    mask = info == 0
    return inverse.to(dtype_original), mask
