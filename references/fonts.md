# 制作用字

仅采用以下已选字体。字体文件不随本包分发，应从官方来源安装并核对实际版本。

| 用途 | 字体 | 官方来源 |
| --- | --- | --- |
| 正文、数字、图表、英文 | Noto Sans SC | [Google Fonts](https://github.com/google/fonts/tree/main/ofl/notosanssc) |
| 衬线标题、引文 | Noto Serif SC | [Google Fonts](https://github.com/google/fonts/tree/main/ofl/notoserifsc) |
| 手书短题、逐字聚合 | 庞门正道粗书体6.0 | [作者发布与授权说明](https://mp.weixin.qq.com/s/LZ_PMNc-3uX-Atmri4OLGQ) |

Noto字体使用SIL OFL 1.1；分发其字体文件时附相应版权和许可证。庞门正道粗书体按作者免费商用声明使用，不将字体文件重新标为AGPL，也不因允许商用就推断允许任意再分发或嵌入。

组装器把显式字体和主题默认字族统一到批准清单，并移除源文件嵌入字体。新稿仍须检查换行、字号、缺字和末字落点。字体检查可用：

```sh
python scripts/check_ppt_fonts.py 新稿.pptx
```
