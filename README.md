# 随便聊 - 匿名陌生人社交应用

## 项目概述

**随便聊** 是一个匿名陌生人社交应用，主打"漂流瓶"式的随机匹配聊天体验。用户可以通过扔瓶子、捞瓶子、随机匹配等方式与陌生人进行匿名交流，同时支持发布和认领寻人公告。

## 产品特色

- 🏺 **漂流瓶系统**：扔瓶子、捞瓶子，传统漂流瓶的现代化体验
- 🔄 **随机匹配**：捞个在线、随机匹配，轻松找到聊天对象
- 📢 **寻人公告**：发布和认领寻人启事，连接有缘人
- 🏆 **魅力值系统**：基于行为的等级体系，解锁更多功能
- 🔒 **隐私保护**：完全匿名，无实名认证，保护隐私安全
- 🎨 **响应式设计**：适配手机和电脑浏览器

## 技术架构

### 前端
- **框架**：React 18
- **构建工具**：Vite
- **UI**：Tailwind CSS + shadcn/ui
- **路由**：React Router DOM
- **状态管理**：React Context
- **通信**：Axios + Socket.io

### 后端
- **框架**：Python + FastAPI
- **数据库**：MongoDB (Mongoose ODM)
- **缓存**：Redis
- **实时通信**：Socket.io
- **身份验证**：JWT + bcrypt
- **文件处理**：Multer
- **验证**：Pydantic

### 部署
- **容器化**：Docker + Docker Compose
- **反向代理**：Nginx
- **数据库**：MongoDB (官方Docker镜像)
- **缓存**：Redis (官方Docker镜像)

## 项目结构

```
anonymous-chat/
├── frontend/                 # 前端应用
│   ├── src/
│   │   ├── components/       # 通用组件
│   │   ├── pages/           # 页面组件
│   │   ├── context/         # 状态管理
│   │   ├── hooks/           # 自定义钩子
│   │   ├── services/        # API服务
│   │   ├── utils/           # 工具函数
│   │   ├── styles/          # 全局样式
│   │   └── main.jsx         # 入口文件
│   ├── public/              # 静态资源
│   ├── package.json         # 依赖配置
│   ├── vite.config.js       # Vite配置
│   └── Dockerfile           # 前端Docker镜像
├── backend/                 # 后端服务
│   ├── src/
│   │   ├── controllers/     # 控制器
│   │   ├── models/          # 数据模型
│   │   ├── routes/          # 路由
│   │   ├── middleware/      # 中间件
│   │   ├── services/        # 业务逻辑
│   │   ├── utils/           # 工具函数
│   │   └── main.py          # 应用入口
│   ├── public/              # 静态资源
│   ├── package.json         # 依赖配置
│   └── Dockerfile           # 后端Docker镜像
├── docker-compose.yml       # Docker Compose配置
├── nginx/                   # Nginx配置
│   └── nginx.conf
└── README.md               # 项目说明
```

## 快速启动

### 环境要求
- Docker Engine 20.10.0+
- Docker Compose 2.0.0+

### 启动步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd anonymous-chat
   ```

2. **构建和启动服务**
   ```bash
   docker-compose up --build
   ```

3. **访问应用**
   - 前端应用：http://localhost:3000
   - 后端API：http://localhost:5000/docs
   - 管理界面：http://localhost:5000/redoc

### 开发模式

如果需要在本地开发，可以单独启动前端和后端服务：

#### 前端开发
```bash
cd frontend
npm install
npm run dev
```

#### 后端开发
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload
```

## 功能说明

### 核心功能

#### 1. 用户系统
- 三种注册方式：手机号、邮箱、随意账号密码
- 登录方式：账号密码、手机号验证码
- 记住登录状态
- 账号安全：无需实名认证

#### 2. 魅力值系统
- **等级体系**：受限 → 观察 → 进阶 → 活跃 → 优质 → 核心
- **功能权限**：不同等级解锁不同功能
- **获取方式**：每日登录、文明发言、行为良好、被点赞、购买会员
- **扣除机制**：发送违规内容、被举报、刷魅力值等

#### 3. 聊天系统
- 文字、图片、文件、表情聊天
- 实时消息推送
- 消息点赞、举报、拉黑功能
- 绿色模式（敏感词过滤）
- 英语模式（仅限英文交流）
- 虚拟人物对话（AI机器人）

#### 4. 匹配系统
- **捞个在线**：从在线用户中随机抽取
- **随机匹配**：双方同时点击进入匹配池
- **匹配优先级**：魅力值≥100的用户优先匹配
- **次数限制**：每日次数受魅力值等级影响

#### 5. 漂流瓶系统
- **扔瓶子**：发送文字+图片，24小时有效期
- **捞瓶子**：从瓶子池中随机捞取
- **审核机制**：自动AI审核+人工抽检
- **沉没机制**：到期或达到捞取上限自动沉没

#### 6. 寻人公告
- **发布权限**：魅力值≥100
- **内容审核**：人工审核，2小时内完成
- **展示形式**：首页轮播，按时间倒序
- **认领机制**：填写验证信息，发布者确认

### 其他功能

#### 隐私设置
- 允许被"捞个在线"发现
- 绿色模式（私聊屏蔽敏感词）
- 夜间模式（深色主题）
- 通知声音控制
- 英语模式
- 位置显示

#### 个人资料
- 头像上传和修改
- 昵称、性别、年龄设置
- 标签管理
- 魅力值展示

#### 增值服务
- 会员特权（去广告、专属标识、次数加成）
- 广告植入（开屏、插屏、原生广告）
- 激励视频（观看视频+魅力值）
- 魅力值直购

## 数据库设计

### 用户表 (users)
存储用户基本信息、设置、魅力值等

### 聊天表 (chats)
存储聊天记录，支持文字、图片、文件消息

### 匹配表 (matches)
存储匹配历史和状态

### 漂流瓶表 (bottles)
存储瓶子内容、投放者、捞取记录等

### 公告表 (announcements)
存储寻人公告内容

### 魅力值历史表 (charm_history)
记录用户魅力值变化

### 其他表
- 黑名单表 (blocks)
- 举报表 (reports)
- 点赞表 (likes)
- 瓶子捞取表 (bottle_picks)
- 瓶子回复表 (bottle_replies)
- 公告认领表 (announcement_claims)

## API接口

### 用户管理
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/profile` - 获取用户资料
- `PUT /api/users/profile` - 更新用户资料
- `PUT /api/users/settings` - 更新用户设置

### 聊天
- `POST /api/chats/message` - 发送消息
- `GET /api/chats/history` - 获取聊天记录
- `POST /api/chats/like` - 点赞消息
- `POST /api/chats/report` - 举报消息
- `POST /api/chats/block` - 拉黑用户

### 匹配
- `POST /api/match/random` - 随机匹配
- `POST /api/match/online` - 捞个在线
- `POST /api/match/cancel` - 取消匹配
- `GET /api/match/status` - 获取匹配状态

### 漂流瓶
- `POST /api/bottles/throw` - 扔瓶子
- `POST /api/bottles/pick` - 捞瓶子
- `POST /api/bottles/reply` - 回复瓶子
- `POST /api/bottles/withdraw` - 撤回瓶子

### 公告
- `POST /api/announcements` - 发布公告
- `GET /api/announcements` - 获取公告列表
- `GET /api/announcements/:id` - 获取公告详情
- `POST /api/announcements/claim` - 认领公告

### 魅力值
- `GET /api/charm/info` - 获取魅力值信息
- `GET /api/charm/history` - 获取魅力值变更历史
- `POST /api/charm/daily-checkin` - 每日签到
- `GET /api/charm/privileges` - 获取权限说明

## 安全考虑

### 密码加密
使用 bcrypt 加密存储密码，安全可靠

### JWT认证
使用 JSON Web Token 进行身份验证，支持自动过期

### CORS保护
配置跨域资源共享，限制访问源

### 输入验证
使用 Pydantic 进行数据验证和清理

### 文件安全
- 支持图片和文件上传
- 文件类型限制和大小限制
- 文件自动检测和防病毒

### 敏感词过滤
内置敏感词库，支持实时过滤

## 性能优化

### 前端优化
- 代码分割和懒加载
- 图片和文件压缩
- CDN加速
- 浏览器缓存

### 后端优化
- MongoDB索引优化
- Redis缓存策略
- API响应压缩
- 连接池管理

### 数据库优化
- 查询优化
- 读写分离
- 数据分片
- 定期清理

## 部署说明

### Docker部署
1. 修改 `docker-compose.yml` 中的环境变量
2. 执行 `docker-compose up -d`
3. 访问 http://localhost:3000

### 生产环境部署
1. 配置域名和SSL证书
2. 优化Nginx配置
3. 配置数据库备份策略
4. 设置监控和日志系统

### 常用命令
```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 清理数据
docker-compose down -v
```

## 开发说明

### 提交规范
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档变更
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试文件变更
- `chore`: 构建过程或辅助工具的变更

### 分支策略
- `main`: 主分支
- `develop`: 开发分支
- `feature/*`: 功能分支
- `hotfix/*`: 紧急修复分支

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交代码
4. 创建Pull Request
5. 等待审核

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过以下方式联系：
- 邮箱：support@example.com
- GitHub Issues：https://github.com/example/anonymous-chat/issues

---

**注意**：这是一个匿名社交应用，请遵守相关法律法规，文明交流。
