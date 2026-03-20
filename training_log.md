# ResNet-18 指纹类型分类训练流程（SD04）

本文件记录本次 ResNet-18 指纹类型分类的完整训练与评估流程。

## 1. 数据集

- 数据集路径：
  `/Users/ye/Documents/fingerprint-system/sd04`
- 数据格式：
  `sd04/png_txt/figs_*/*.png` + `sd04/png_txt/figs_*/*.txt`
- 标签来源：
  每个 `.txt` 文件中的 `Class: X`
  - A: arch
  - L: left_loop
  - R: right_loop
  - W: whorl
  - T: tented_arch（本次合并为 arch）

## 2. 模型与训练设置

- 模型：ResNet-18（ImageNet 预训练）
- 输入：灰度图 1 通道
- 类别：4 类（arch / left_loop / right_loop / whorl）
- 训练参数（CPU 轻量模式）：
  - epochs: 10
  - batch_size: 16
  - img_size: 192
  - num_workers: 0
  - threads: 2
  - val_split: 0.2
  - merge_tented_arch: true

## 3. 训练命令

```bash
cd /Users/ye/Documents/fingerprint-system
conda run -n fingerprint python scripts/train_resnet_classifier.py \
  --data-dir /Users/ye/Documents/fingerprint-system/sd04 \
  --epochs 10 \
  --batch-size 16 \
  --img-size 192 \
  --num-workers 0 \
  --threads 2 \
  --merge-tented-arch \
  --output weights/resnet18_fingerprint.pth
```

## 4. 训练日志

```
Epoch 1/10  loss=0.4547  val_acc=0.9237
Epoch 2/10  loss=0.1883  val_acc=0.9363
Epoch 3/10  loss=0.1469  val_acc=0.9187
Epoch 4/10  loss=0.1136  val_acc=0.9325
Epoch 5/10  loss=0.0827  val_acc=0.9313
Epoch 6/10  loss=0.0761  val_acc=0.9525
Epoch 7/10  loss=0.0424  val_acc=0.9413
Epoch 8/10  loss=0.0494  val_acc=0.9437
Epoch 9/10  loss=0.0489  val_acc=0.9337
Epoch 10/10  loss=0.0481  val_acc=0.9363
Best validation accuracy: 0.9525
Saved weights to weights/resnet18_fingerprint.pth
```

## 5. 评估命令

```bash
cd /Users/ye/Documents/fingerprint-system
conda run -n fingerprint python scripts/eval_resnet_classifier.py \
  --data-dir /Users/ye/Documents/fingerprint-system/sd04 \
  --weights weights/resnet18_fingerprint.pth \
  --img-size 192 \
  --num-workers 0 \
  --threads 2 \
  --merge-tented-arch
```

## 6. 评估结果

```
Accuracy: 0.9865
Confusion matrix:
[[1586   12    2    0]
 [  10  787    0    3]
 [  22    0  777    1]
 [   0    1    3  796]]
```

