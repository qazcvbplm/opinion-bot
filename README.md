✅ 一、下载安装 Python（官方方式）
1️⃣ 打开官网

👉 https://www.python.org

点击顶部 Downloads
网站会自动推荐 Python 3.12 / 3.11（Windows）

✔ Python 3.10、3.11、3.12 都可以
✔ 一般推荐 3.11 或 3.12

2️⃣ 下载 Windows 安装包

点击：

Download Python 3.x.x


下载的是：

python-3.x.x-amd64.exe

⚠️ 二、安装时【最重要的一步】

双击安装包后，一定要勾选下面这个选项：

☑ Add Python to PATH

然后再点击：

👉 Install Now

📌 如果你忘了勾这个，后面命令行会用不了 python

⏳ 三、等待安装完成

看到：

Setup was successful


说明安装成功 ✅

✅ 四、验证是否安装成功
1️⃣ 打开命令行

按键盘：

Win + R → 输入 cmd → 回车

2️⃣ 输入：
python --version


正确结果示例：

Python 3.11.6


再试试：

pip --version

❌ 常见问题 & 解决办法
❓ 输入 python 提示不是命令

原因：PATH 没加

✅ 解决方案（推荐）：

重新运行安装包

选择 Modify

勾选 Add Python to PATH

Next → Install

❓ 出现 Microsoft Store

Windows 有时会劫持 python

✅ 解决：

打开 设置

搜索 应用执行别名

关闭：

python.exe

python3.exe

✅ 五、（可选）安装开发工具
升级 pip（推荐）
python -m pip install --upgrade pip

安装常用库测试
pip install requests