# 📚 Git 工作流程与分支策略

本文档定义了 VirtualChemLab 项目的 Git 版本控制规范和最佳实践。

---

## 📋 目录

- [分支策略](#-分支策略)
- [工作流程](#-工作流程)
- [提交规范](#-提交规范)
- [版本管理](#-版本管理)
- [代码审查](#-代码审查)
- [最佳实践](#-最佳实践)

---

## 🌿 分支策略

我们采用 **Git Flow** 工作流的简化版本，结合项目实际需求进行调整。

### 主要分支

#### `main` 分支
- **用途**: 生产环境代码
- **保护级别**: 🔒 完全保护
- **合并要求**: 必须通过 PR + 代码审查
- **特点**: 
  - 始终处于可部署状态
  - 每次合并都会触发版本发布
  - 只能从 `release/*` 或 `hotfix/*` 合并

#### `develop` 分支
- **用途**: 开发主分支
- **保护级别**: 🔒 部分保护
- **合并要求**: 必须通过 PR
- **特点**:
  - 最新的开发代码
  - 可能不稳定
  - 每日集成测试

### 支持分支

#### `feature/*` - 功能分支
- **命名**: `feature/功能名称`
- **来源**: 从 `develop` 创建
- **合并到**: `develop`
- **生命周期**: 功能开发期间
- **示例**:
  ```bash
  feature/dark-mode
  feature/experiment-export
  feature/teacher-dashboard
  ```

#### `bugfix/*` - Bug修复分支
- **命名**: `bugfix/bug描述`
- **来源**: 从 `develop` 创建
- **合并到**: `develop`
- **生命周期**: Bug修复期间
- **示例**:
  ```bash
  bugfix/login-error
  bugfix/chart-rendering
  ```

#### `release/*` - 发布分支
- **命名**: `release/版本号`
- **来源**: 从 `develop` 创建
- **合并到**: `main` 和 `develop`
- **生命周期**: 版本发布准备期间
- **示例**:
  ```bash
  release/v2.1.0
  release/v2.2.0-beta
  ```

#### `hotfix/*` - 紧急修复分支
- **命名**: `hotfix/问题描述`
- **来源**: 从 `main` 创建
- **合并到**: `main` 和 `develop`
- **生命周期**: 紧急修复期间
- **示例**:
  ```bash
  hotfix/security-vulnerability
  hotfix/critical-crash
  ```

### 分支命名规范

```
类型/简短描述

规则:
- 全部小写
- 使用连字符 (-)
- 简洁明了
- 使用英文（推荐）或拼音

✅ 好的命名:
feature/user-authentication
bugfix/memory-leak
release/v2.0.0

❌ 不好的命名:
Feature/UserAuth
fix_bug
新功能
```

---

## 🔄 工作流程

### 1. 功能开发流程

```bash
# 1. 更新 develop 分支
git checkout develop
git pull origin develop

# 2. 创建功能分支
git checkout -b feature/awesome-feature

# 3. 开发并提交
git add .
git commit -m "feat: add awesome feature"

# 4. 推送到远程
git push origin feature/awesome-feature

# 5. 创建 Pull Request
# 在 GitHub/GitLab 上创建 PR: feature/awesome-feature -> develop

# 6. 代码审查通过后合并
# 由维护者合并

# 7. 删除本地分支
git checkout develop
git pull origin develop
git branch -d feature/awesome-feature
```

### 2. Bug修复流程

```bash
# 1. 从 develop 创建 bugfix 分支
git checkout develop
git pull origin develop
git checkout -b bugfix/fix-issue-123

# 2. 修复并提交
git add .
git commit -m "fix: resolve issue #123"

# 3. 推送并创建 PR
git push origin bugfix/fix-issue-123
# 创建 PR: bugfix/fix-issue-123 -> develop
```

### 3. 发布流程

```bash
# 1. 从 develop 创建 release 分支
git checkout develop
git pull origin develop
git checkout -b release/v2.1.0

# 2. 更新版本号
# 编辑 pyproject.toml, src/__init__.py 等
vim pyproject.toml
# version = "2.1.0"

# 3. 更新 CHANGELOG
vim CHANGELOG.md

# 4. 提交版本更新
git add .
git commit -m "chore: bump version to 2.1.0"

# 5. 合并到 main
git checkout main
git pull origin main
git merge --no-ff release/v2.1.0
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin main --tags

# 6. 合并回 develop
git checkout develop
git merge --no-ff release/v2.1.0
git push origin develop

# 7. 删除 release 分支
git branch -d release/v2.1.0
```

### 4. 紧急修复流程

```bash
# 1. 从 main 创建 hotfix 分支
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug

# 2. 修复并提交
git add .
git commit -m "fix: critical security issue"

# 3. 合并到 main
git checkout main
git merge --no-ff hotfix/critical-bug
git tag -a v2.0.1 -m "Hotfix v2.0.1"
git push origin main --tags

# 4. 合并到 develop
git checkout develop
git merge --no-ff hotfix/critical-bug
git push origin develop

# 5. 删除 hotfix 分支
git branch -d hotfix/critical-bug
```

---

## 📝 提交规范

### Conventional Commits

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范。

#### 格式

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Type 类型

| Type | 说明 | 示例 | 影响版本 |
|------|------|------|----------|
| `feat` | 新功能 | feat: add dark mode | MINOR |
| `fix` | Bug修复 | fix: resolve memory leak | PATCH |
| `docs` | 文档更新 | docs: update README | - |
| `style` | 代码格式 | style: format with ruff | - |
| `refactor` | 代码重构 | refactor: simplify logic | - |
| `perf` | 性能优化 | perf: optimize rendering | PATCH |
| `test` | 测试相关 | test: add unit tests | - |
| `build` | 构建系统 | build: update dependencies | - |
| `ci` | CI/CD | ci: add GitHub Actions | - |
| `chore` | 其他杂项 | chore: update .gitignore | - |
| `revert` | 回滚提交 | revert: revert commit abc123 | - |

#### Scope 范围（可选）

```
ui        - UI界面
core      - 核心功能
api       - API接口
db        - 数据库
auth      - 认证授权
experiment - 实验相关
license   - 许可证
docs      - 文档
test      - 测试
```

#### 示例

```bash
# 简单提交
git commit -m "feat: add experiment export functionality"

# 带 scope
git commit -m "fix(ui): resolve chart rendering issue"

# 详细描述
git commit -m "feat(experiment): add titration simulation

- Implement acid-base titration
- Add pH indicator color changes
- Support custom reagent concentrations

Closes #123"

# Breaking change
git commit -m "feat!: redesign API endpoints

BREAKING CHANGE: API v1 endpoints are removed.
Use /api/v2/* instead of /api/v1/*"
```

### 提交最佳实践

#### ✅ 好的提交

```bash
# 清晰、具体
git commit -m "fix: prevent race condition in experiment submission"

# 包含上下文
git commit -m "perf(ui): reduce initial load time from 3s to 1s"

# 引用 Issue
git commit -m "feat: add teacher dashboard

Implements #45"
```

#### ❌ 不好的提交

```bash
# 太模糊
git commit -m "fix bug"

# 混合多个更改
git commit -m "add feature and fix bug and update docs"

# 无意义
git commit -m "update"
git commit -m "WIP"
```

---

## 🏷️ 版本管理

### 语义化版本

遵循 [Semantic Versioning 2.0.0](https://semver.org/)

```
MAJOR.MINOR.PATCH[-prerelease][+build]

例如:
2.1.0          # 稳定版本
2.2.0-beta.1   # 测试版本
2.2.0-rc.1     # 候选版本
2.2.0+20250107 # 带构建号
```

#### 版本号规则

| 类型 | 何时递增 | 示例 |
|------|----------|------|
| **MAJOR** | 不兼容的 API 变更 | 1.0.0 → 2.0.0 |
| **MINOR** | 向后兼容的新功能 | 1.0.0 → 1.1.0 |
| **PATCH** | 向后兼容的问题修正 | 1.0.0 → 1.0.1 |

#### 预发布版本

```bash
# Alpha - 内部测试
2.0.0-alpha.1
2.0.0-alpha.2

# Beta - 公开测试
2.0.0-beta.1
2.0.0-beta.2

# RC - 发布候选
2.0.0-rc.1
2.0.0-rc.2

# 稳定版
2.0.0
```

### Git 标签

```bash
# 创建注释标签
git tag -a v2.1.0 -m "Release version 2.1.0

Features:
- Add dark mode support
- Implement experiment export
- Teacher dashboard

Bug Fixes:
- Fix memory leak in chart rendering
- Resolve login authentication issue

Performance:
- Optimize initial load time
- Reduce memory usage by 30%
"

# 推送标签
git push origin v2.1.0

# 推送所有标签
git push origin --tags

# 查看标签
git tag -l

# 查看标签详情
git show v2.1.0

# 删除本地标签
git tag -d v2.1.0

# 删除远程标签
git push origin :refs/tags/v2.1.0
```

### 版本文件更新

发布新版本时需要更新以下文件：

1. **pyproject.toml**
   ```toml
   [project]
   version = "2.1.0"
   ```

2. **src/__init__.py**
   ```python
   __version__ = "2.1.0"
   ```

3. **CHANGELOG.md**
   ```markdown
   ## [2.1.0] - 2025-01-07
   
   ### Added
   - New feature X
   
   ### Fixed
   - Bug Y
   ```

4. **package.json** (如果有)
   ```json
   {
     "version": "2.1.0"
   }
   ```

---

## 🔍 代码审查

### Pull Request 流程

1. **创建 PR**
   - 标题清晰明了
   - 填写 PR 模板
   - 关联相关 Issue

2. **自动检查**
   - ✅ CI/CD 测试通过
   - ✅ 代码风格检查通过
   - ✅ 覆盖率达标

3. **代码审查**
   - 至少 1 人审查（小改动）
   - 至少 2 人审查（重大改动）
   - 解决所有评论

4. **合并**
   - 使用 Squash Merge（功能分支）
   - 使用 No-FF Merge（release/hotfix）

### PR 模板

````markdown
## 📋 变更类型

- [ ] 新功能 (feat)
- [ ] Bug修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 性能优化 (perf)
- [ ] 测试相关 (test)

## 📝 变更描述

<!-- 描述你的更改 -->

## 🔗 相关 Issue

Closes #(issue)

## 📸 截图/演示

<!-- 如果是 UI 变更，添加截图 -->

## ✅ 检查清单

- [ ] 代码通过所有测试
- [ ] 代码通过 Linter 检查
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 遵循代码规范
- [ ] 无合并冲突

## 🧪 测试说明

<!-- 如何测试你的更改 -->

## 📚 附加信息

<!-- 其他需要说明的信息 -->
````

### 审查检查清单

#### 代码质量
- [ ] 代码逻辑清晰易懂
- [ ] 遵循项目代码规范
- [ ] 有适当的注释
- [ ] 无冗余代码
- [ ] 无硬编码值

#### 功能
- [ ] 实现了预期功能
- [ ] 边界情况处理
- [ ] 错误处理完善
- [ ] 无性能问题

#### 测试
- [ ] 有单元测试
- [ ] 测试覆盖充分
- [ ] 测试用例合理

#### 文档
- [ ] API 文档更新
- [ ] README 更新
- [ ] CHANGELOG 更新

---

## 💡 最佳实践

### 1. 保持提交原子化

```bash
# ✅ 好的做法 - 每个提交只做一件事
git commit -m "feat: add user login"
git commit -m "feat: add password validation"
git commit -m "test: add login tests"

# ❌ 不好的做法 - 一个提交做多件事
git commit -m "add login, validation, and tests"
```

### 2. 经常同步

```bash
# 每天开始工作前
git checkout develop
git pull origin develop

# 定期 rebase (保持历史清晰)
git checkout feature/my-feature
git rebase develop

# 如果有冲突，解决后继续
git rebase --continue
```

### 3. 使用 .gitignore

确保不提交：
- 临时文件
- IDE 配置
- 编译产物
- 敏感信息
- 用户数据

### 4. 编写有意义的合并信息

```bash
# ✅ 使用 --no-ff 保留分支历史
git merge --no-ff feature/awesome-feature -m "Merge feature: awesome feature

- Implemented X
- Fixed Y
- Updated Z"

# ❌ 避免快进合并（丢失分支信息）
git merge feature/awesome-feature
```

### 5. 保护重要分支

在 GitHub/GitLab 设置中：
- [x] 禁止直接推送到 main
- [x] 禁止直接推送到 develop
- [x] 要求 PR 审查
- [x] 要求状态检查通过
- [x] 要求最新代码才能合并

### 6. 使用 Git Hooks

```bash
# 安装 pre-commit
pip install pre-commit

# 创建 .pre-commit-config.yaml
# (详见后续章节)

# 安装 hooks
pre-commit install

# 手动运行
pre-commit run --all-files
```

### 7. 清理本地分支

```bash
# 查看所有分支
git branch -a

# 删除已合并的本地分支
git branch --merged | grep -v "\*\|main\|develop" | xargs -n 1 git branch -d

# 清理远程已删除的分支引用
git fetch --prune
```

### 8. 紧急情况处理

```bash
# 撤销最后一次提交（保留更改）
git reset --soft HEAD~1

# 撤销最后一次提交（丢弃更改）
git reset --hard HEAD~1

# 修改最后一次提交
git commit --amend

# 暂存当前工作
git stash
git stash pop

# 回滚到特定提交
git revert <commit-hash>
```

---

## 🛠️ Git 配置

### 全局配置

```bash
# 设置用户信息
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 设置默认编辑器
git config --global core.editor "vim"

# 启用颜色输出
git config --global color.ui auto

# 设置换行符处理
git config --global core.autocrlf input  # Mac/Linux
git config --global core.autocrlf true   # Windows

# 设置默认分支名
git config --global init.defaultBranch main

# 设置 pull 策略
git config --global pull.rebase false
```

### 项目配置

```bash
# .git/config 或使用命令
git config user.name "Project Name"
git config user.email "project@example.com"
```

### 别名配置

```bash
# 常用别名
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual 'log --graph --oneline --all'
```

---

## 📊 可视化工具

### 推荐工具

1. **命令行**
   - `git log --graph --oneline --all`
   - `tig` (终端 Git 浏览器)

2. **GUI 工具**
   - GitHub Desktop
   - GitKraken
   - SourceTree
   - VS Code Git Graph

3. **Web 界面**
   - GitHub
   - GitLab
   - Gitea

---

## 🎯 工作流示例

### 完整的功能开发示例

```bash
# Day 1: 开始新功能
git checkout develop
git pull origin develop
git checkout -b feature/user-profile

# 开发...
git add src/ui/profile.py
git commit -m "feat(ui): add user profile page layout"

git add src/api/profile.py
git commit -m "feat(api): add profile data endpoint"

git push origin feature/user-profile

# Day 2: 继续开发
git add tests/test_profile.py
git commit -m "test(ui): add profile page tests"

# 同步 develop 的最新更改
git fetch origin develop
git rebase origin/develop

# 解决冲突（如果有）
git add .
git rebase --continue

git push origin feature/user-profile --force-with-lease

# Day 3: 完成并创建 PR
# 在 GitHub 创建 PR: feature/user-profile -> develop

# 审查通过后，维护者合并

# Day 4: 清理
git checkout develop
git pull origin develop
git branch -d feature/user-profile
```

---

## 📚 参考资源

### 官方文档
- [Git 官方文档](https://git-scm.com/doc)
- [Git Book (中文)](https://git-scm.com/book/zh/v2)
- [GitHub Guides](https://guides.github.com/)

### 工作流
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [GitLab Flow](https://docs.gitlab.com/ee/topics/gitlab_flow.html)

### 提交规范
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Angular Commit Guidelines](https://github.com/angular/angular/blob/master/CONTRIBUTING.md#commit)

### 语义化版本
- [Semantic Versioning](https://semver.org/)

---

## 🆘 常见问题

### Q1: 如何撤销已推送的提交？

```bash
# 方法1: Revert (推荐 - 保留历史)
git revert <commit-hash>
git push origin <branch>

# 方法2: Reset (危险 - 改写历史)
git reset --hard <commit-hash>
git push origin <branch> --force-with-lease
```

### Q2: 如何解决合并冲突？

```bash
# 1. 拉取最新代码
git pull origin develop

# 2. 查看冲突文件
git status

# 3. 手动解决冲突
# 编辑冲突文件，删除 <<<<, ====, >>>> 标记

# 4. 标记为已解决
git add <resolved-files>

# 5. 完成合并
git commit
```

### Q3: 误删分支怎么办？

```bash
# 查找删除的分支
git reflog

# 恢复分支
git checkout -b <branch-name> <commit-hash>
```

### Q4: 如何修改历史提交信息？

```bash
# 修改最后一次提交
git commit --amend

# 修改多个提交
git rebase -i HEAD~3  # 修改最近3个提交

# 在编辑器中将 pick 改为 reword/edit
# 保存后按提示操作
```

---

<div align="center">

**遵循规范，让协作更顺畅！** 🚀

*最后更新: 2025-01-07*

</div>


