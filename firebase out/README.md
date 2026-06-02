# 昨日头条 (Yesterday's Headlines)

这是一个基于 Next.js 15 和 Genkit AI 构建的高端新闻阅读应用。

## 部署至 GitHub & Vercel (手动迁移指南)

由于 Firebase App Hosting 暂时不可用，请按照以下步骤将代码迁移到 GitHub 并部署到 Vercel：

### 第一步：从 Firebase Studio 下载代码
1. 在 Firebase Studio 界面（本 IDE），点击工具栏中的 **"Download"** 图标（通常在右上角）。
2. 这将下载一个包含所有源代码的 `.zip` 文件。
3. 在你的本地电脑上解压该文件。

### 第二步：在 GitHub 上创建新仓库
1. 登录你的 GitHub 账号，访问 [github.com/new](https://github.com/new)。
2. 仓库名称填入 `yesterdays-headlines`。
3. 点击 **"Create repository"**。

### 第三步：上传代码到 GitHub
1. 在 GitHub 仓库页面，点击 **"uploading an existing file"** 链接。
2. 将你本地解压出的所有文件（不包括 `node_modules`）拖入浏览器。
3. 点击 **"Commit changes"**。

### 第四步：部署到 Vercel
1. 登录 [Vercel](https://vercel.com)。
2. 点击 **"Add New > Project"**。
3. 选择你刚刚创建的 GitHub 仓库。
4. Vercel 会自动检测到它是 Next.js 项目。直接点击 **"Deploy"**。

---

## 技术栈
- **框架**: Next.js 15 (App Router)
- **UI**: React + Tailwind CSS + ShadCN UI
- **AI**: Genkit (Google Gemini)
- **数据源**: GitHub 静态 JSON (实时更新)
