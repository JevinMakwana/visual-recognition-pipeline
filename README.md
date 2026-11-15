# Visual Recognition Pipeline

Multi-label image classification and semantic segmentation on a PASCAL VOC–style dataset (20 object classes), built with PyTorch. The project also includes PCA written from scratch in NumPy and statistical tests comparing two segmentation models.

## Dataset

2,913 natural images labelled with 20 object classes:

| Split | Images | Labels |
|---|---|---|
| Train | 2,200 | Multi-label class vectors (`labels.csv`) and pixel-level segmentation masks |
| Test | 713 | None |

**Classes:** aeroplane, bicycle, bird, boat, bottle, bus, car, cat, chair, cow, diningtable, dog, horse, motorbike, person, pottedplant, sheep, sofa, train, tvmonitor.

**Segmentation masks** are 8-bit PNGs in which each pixel holds a class index: 0 is background, 1–20 are the object classes, and 255 marks object boundaries, which training and evaluation ignore.

```
data/Dataset/
├── train/
│   ├── images/               # 2,200 JPEG images
│   ├── segmentation_masks/   # 2,200 PNG masks
│   └── labels.csv            # image_id + one 0/1 column per class
└── test/
    └── images/               # 713 JPEG images
```

The dataset isn't stored in this repository. If `data/Dataset` is missing, the notebooks download it automatically from [Google Drive](https://drive.google.com/file/d/1YH4ePf17TTYU_wh2Rc5BF3ZhGmn42Cw7/view) (about 314 MB) through `data_utils.ensure_dataset()`.

## Models

Only the backbones use ImageNet-pretrained weights. The classification head, the segmentation decoder and the training code are written in this repository.

### PCA (NumPy)

- **Global PCA:** grayscale images are resized to 32 × 32 and flattened into 1,024-value vectors. The data is centred, and the principal components come from SVD.
- **Patch-based PCA:** full-resolution grayscale images are cut into 12 × 12 patches (144 values each), and the components are the eigenvectors of the patch covariance matrix.

### Classification

- **Backbone:** ResNet-50 with ImageNet weights (`IMAGENET1K_V2`). Its final pooling and fully connected layers are removed.
- **Head (custom):** global average pooling → Linear 2048→512 → BatchNorm → ReLU → Dropout 0.35 → Linear 512→256 → BatchNorm → ReLU → Dropout 0.25 → Linear 256→20 → sigmoid.
- **Input:** images are resized to 336, then cropped to 320 × 320. Training adds random crops, flips, colour jitter and rotation.
- **Loss:** 0.75 × BCE-with-logits plus 0.25 × focal loss (γ = 2). BCE uses per-class positive weights to offset class imbalance.
- **Training:**
  - 95/5 train/validation split
  - 52 epochs, batch size 16
  - AdamW (learning rate 2.5e-4, weight decay 1e-4) with a cosine schedule
  - mixed precision, gradient clipping at 1.0
- **Inference:** a class is predicted when its probability is ≥ 0.5.

### Segmentation

- **Encoder:** ResNet-50 with ImageNet weights. Features come from all four stages, at 1/4, 1/8, 1/16 and 1/32 of the input resolution.
- **Decoder (custom):** a top-down path with skip connections, similar to U-Net and FPN:
  1. The deepest feature map (stage 4) is reduced to 256 channels.
  2. It is upsampled and fused with stage 3, giving 256 channels.
  3. That is upsampled and fused with stage 2, giving 192 channels.
  4. That is upsampled and fused with stage 1, giving 128 channels.
  5. The result is upsampled to the input size, and a 1×1 convolution produces scores for 21 classes.

  Each fusion step is two 3×3 Conv–BatchNorm–ReLU blocks.
- **Input:** 384 × 384. Training adds random crops, flips and colour jitter.
- **Loss:** class-weighted cross-entropy (weights from inverse square-root class frequency, with label smoothing, ignoring boundary pixels) plus soft Dice loss.
- **Training:**
  - 90/10 train/validation split
  - 32 epochs, batch size 4
  - AdamW with a cosine schedule, mixed precision
  - Two variants are trained for the statistical comparison:

  | Variant | Learning rate | Dice weight | Label smoothing |
  |---|---|---|---|
  | A | 1.5e-4 | 0.60 | 0.02 |
  | B | 2.0e-4 | 0.50 | 0.01 |

- **Inference:** predictions on the image and its horizontal mirror are averaged, then the mask is resized back to the original image size.

## Evaluation

| Task | Metric |
|---|---|
| Classification | **Mean per-image F1:** the predicted class set for each image is compared with the true set using a fixed 0.5 threshold, and the F1 scores are averaged over images. |
| Segmentation | **Mean IoU (mIoU)** over the object classes, ignoring boundary pixels. |

The Kaggle leaderboard score is 0.5 × classification F1 + 0.5 × segmentation mIoU.

**Statistical tests** compare the two segmentation variants on the same validation images, using each image's mIoU:

- a two-sided **Wilcoxon signed-rank test** on the paired differences (mIoU A − mIoU B), at α = 0.05. Wilcoxon is used instead of a paired t-test because IoU differences are bounded and skewed, so they aren't normally distributed.
- a **bootstrap 95% confidence interval** (B = 1,000 resamples, percentile method) for the better model's mean mIoU

## Results

All results are on held-out validation images from the training set, because the test set has no labels.

### PCA (global, 32 × 32, 300 training images)

| Components (k) | Explained variance | Reconstruction MSE |
|---|---|---|
| 8 | 67.83% | 0.01844 |
| 16 | 77.67% | 0.01279 |
| 32 | 86.18% | 0.00792 |
| 64 | 92.97% | 0.00402 |
| 128 | 97.67% | 0.00134 |

With k = 32, PCA keeps over 86% of the variance using 1/32 of the original dimensions.

### Classification

| Metric | Value |
|---|---|
| Best validation mean F1 | **0.8535** (epoch 49) |

### Segmentation

| Variant | Validation mIoU |
|---|---|
| **A** | **0.6562** |
| B | 0.6305 |

Variant A is used for the submission. It has a higher median per-image mIoU, less spread, and scores higher than B on most images.

### Statistical tests

| Test | Result |
|---|---|
| Wilcoxon signed-rank (n = 110 image pairs) | W = 2416.0, two-sided p = **0.0577** |
| Best model (A): mean per-image mIoU | 0.6505 |
| Bootstrap mean (B = 1,000) | 0.6498 |
| Bootstrap standard error | 0.0301 |
| 95% confidence interval (percentile) | **[0.5868, 0.7066]** |

At α = 0.05 the test does not reject H₀ (equal median performance), though the result is borderline. Variant A's 2.5-point mIoU advantage is suggestive but not statistically significant on this sample.
