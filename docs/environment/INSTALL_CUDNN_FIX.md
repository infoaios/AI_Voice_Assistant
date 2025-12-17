# Install cuDNN - Working Method

## ✅ Solution: Use conda-forge

The NVIDIA conda channel doesn't have Windows packages for cuDNN. Use conda-forge instead:

```batch
conda activate voice_assistant_gpu3050
conda install -c conda-forge cudnn -y
```

## Alternative: pip method

If conda-forge doesn't work, use pip:

```batch
conda activate voice_assistant_gpu3050
pip install nvidia-pyindex
pip install nvidia-cudnn
```

## ✅ Verify

After installation:
```batch
python -c "import torch; x = torch.randn(1, 1, device='cuda'); _ = torch.nn.functional.conv2d(x, torch.randn(1, 1, 1, 1, device='cuda')); print('SUCCESS: cuDNN working!')"
```

## 🚀 Then Run

```batch
python main.py
```

---

**Note**: I've updated `env/setup_and_run.bat` to use conda-forge first (which works on Windows), and updated all YAML files to use conda-forge instead of the NVIDIA channel.

