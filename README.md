# 映序 PPT · ppt-motion-kit

把讲稿和资料转成可编辑动画PPT：先建内容大纲与视觉方案，再按信息关系选择原生动画组件，保留完整上下页状态链，最后在目标软件实播验收。

当前为 **v0.1.1 已验证子集**，含 **23个组件、86页**，覆盖开场、目录、图文正文、重点突出、数据与过程、结尾。包含源组件和字体变体，不能把数量理解为23种独立机制。完整418条来源的组件化尚未完成，不在此包虚标覆盖。

## 下载与安装

从本仓库的 [Releases](https://github.com/QGYB/ppt-motion-kit/releases/latest) 下载 `ppt-motion-kit-v0.1.1.skill.zip`。这是含原生PPT资产的完整安装包；GitHub自动生成的“Source code”压缩包只含代码和元数据。

解压后将整个`ppt-motion-kit`目录放到你的AI工具的Skills目录，例如Codex的`~/.codex/skills/`。Python环境安装：

```sh
python -m pip install -r requirements.txt
python scripts/library.py doctor
```

需要Python 3.10以上。PPTX结构组装跨平台；历史动态验证使用Windows WPS。在其他演示软件或新环境中，仍需实际播放。先安装批准字体，详见[字体](references/fonts.md)。

## 使用

向AI提供资料并调用：

> 使用 $ppt-motion-kit 读取我的讲稿和要求，先给出大纲与几张视觉样图，再按内容选择动画组件，制作可编辑PPT，并复核每处衔接。

执行工具也可直接使用：

```sh
python scripts/library.py list --role 开场
python scripts/library.py inspect vid-0299-rhythmic-timeline --bindings
python scripts/library.py assemble examples/timeline.json --output outputs/timeline.pptx
python scripts/check_ppt_fonts.py outputs/timeline.pptx
```

示例演示调用接口，保留源占位内容；制作实际演示须按绑定替换全部相关实体。引擎生成的`.reuse.json`区分结构保留与待做的动态验收，不继承历史通过状态。

查看[组件目录](references/catalog.md)、[绑定契约](references/native-contracts.md)及[Skill入口](SKILL.md)。大文件只在需要时从磁盘读取，不会把全部PPT送入模型上下文。

## 仓库与完整包

Git仓库保存Skill、工具、绑定、SHA清单和历史验证摘要。原生PPT通过Release完整包交付，不把大型二进制版本反复写入Git历史。克隆源码后如缺PPT，请下载完整安装包再运行。

每个组件保留出处、范围与限制。跨模块接口、额外图片数量、任意字数、循环重入和整个新稿不属于自动通过范围。新稿须完成内容、字体、视觉与真实动态检查。

## 许可

提供者已明确确认组件为其自制，并授权全部公开。本仓库的Skill指引、工具代码及完整组件包统一采用 [GNU AGPL-3.0-only](LICENSE)。字体及软件依赖保留各自许可证，详见[依赖与授权说明](THIRD_PARTY_NOTICES.md)。
