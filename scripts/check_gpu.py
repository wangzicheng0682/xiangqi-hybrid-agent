import torch

print(f'CUDA可用: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'当前设备: {torch.cuda.current_device()}')
    print(f'GPU名称: {torch.cuda.get_device_name(0)}')
    print(f'GPU内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
    print(f'GPU已用: {torch.cuda.memory_allocated(0) / 1024**3:.1f} GB')
    print(f'GPU缓存: {torch.cuda.memory_reserved(0) / 1024**3:.1f} GB')
    
    x = torch.randn(10000, 10000).cuda()
    y = torch.randn(10000, 10000).cuda()
    z = torch.mm(x, y)
    
    print(f'\n矩阵乘法后:')
    print(f'GPU已用: {torch.cuda.memory_allocated(0) / 1024**3:.1f} GB')
    print(f'GPU缓存: {torch.cuda.memory_reserved(0) / 1024**3:.1f} GB')
