// download.mjs — 从 GitHub 下载 cut.skill 仓库
//
// 优先用 git clone（开发者机器都有 git，最可靠）
// 失败则用 HTTPS 下载 zip 并解压（纯 Node.js 内置模块，无第三方依赖）
//
// 不用 tar.gz 是因为 Node.js 内置没有 tar 解压器。
// GitHub 也提供 zip 下载，zip 可以用 unzip 命令（macOS/Linux 自带，Windows 也有）。

import { execSync } from 'node:child_process';
import { mkdtempSync, rmSync, existsSync, writeFileSync, unlinkSync, readdirSync, renameSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const HOME = homedir();

// ---------------------------------------------------------------------------
// 方法 1: git clone（首选）
// ---------------------------------------------------------------------------

export function downloadViaGit(repo, ref = 'main') {
  const tmpDir = mkdtempSync(join(HOME, '.cut-skill-tmp-'));
  try {
    execSync(
      `git clone --depth 1 --branch ${ref} https://github.com/${repo}.git "${tmpDir}"`,
      { stdio: 'pipe' }
    );
    if (!existsSync(join(tmpDir, 'SKILL.md'))) {
      throw new Error('下载的仓库不包含 SKILL.md，可能不是有效的 cut.skill 仓库');
    }
    // 删除 .git 目录，避免复制时带走
    rmSync(join(tmpDir, '.git'), { recursive: true, force: true });
    return tmpDir;
  } catch (e) {
    rmSync(tmpDir, { recursive: true, force: true });
    throw new Error(`git clone 失败: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// 方法 2: HTTPS + unzip（备选）
// ---------------------------------------------------------------------------

export async function downloadViaHttps(repo, ref = 'main') {
  const tmpDir = mkdtempSync(join(HOME, '.cut-skill-tmp-'));
  const zipPath = join(tmpDir, 'repo.zip');

  try {
    // GitHub zip URL 会重定向，Node 18+ fetch 自动 follow
    const url = `https://api.github.com/repos/${repo}/zipball/${ref}`;
    const res = await fetch(url, {
      headers: { 'User-Agent': 'cut-skill-installer' },
      redirect: 'follow',
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    const buf = Buffer.from(await res.arrayBuffer());
    writeFileSync(zipPath, buf);

    // 用系统 unzip 命令解压
    // macOS/Linux: unzip 命令；Windows: tar -xf 或 powershell Expand-Archive
    const platform = process.platform;
    let extractCmd;
    if (platform === 'win32') {
      // Windows 用 PowerShell Expand-Archive
      extractCmd = `powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${tmpDir}' -Force"`;
    } else {
      // macOS/Linux 用 unzip
      extractCmd = `unzip -q '${zipPath}' -d '${tmpDir}'`;
    }
    execSync(extractCmd, { stdio: 'pipe' });

    // 删除 zip
    try { unlinkSync(zipPath); } catch {}

    // GitHub zipball 解压后会有一个顶层目录（如 ygtec-cut.skill-abc123/）
    // 找到它，把里面的内容移到 tmpDir 根
    const entries = readdirSync(tmpDir, { withFileTypes: true })
      .filter(d => d.isDirectory());
    const topLevelDir = entries.find(d => d.name !== '__MACOSX');
    if (topLevelDir) {
      const inner = join(tmpDir, topLevelDir.name);
      const items = readdirSync(inner);
      for (const item of items) {
        renameSync(join(inner, item), join(tmpDir, item));
      }
      rmSync(inner, { recursive: true, force: true });
    }

    // 验证
    if (!existsSync(join(tmpDir, 'SKILL.md'))) {
      throw new Error('下载的仓库不包含 SKILL.md，可能不是有效的 cut.skill 仓库');
    }
    return tmpDir;
  } catch (e) {
    rmSync(tmpDir, { recursive: true, force: true });
    throw new Error(`HTTPS 下载失败: ${e.message}`);
  }
}

// ---------------------------------------------------------------------------
// 统一入口：优先 git，失败回退 HTTPS
// ---------------------------------------------------------------------------

export async function downloadSkill(repo = 'ygtec/cut.skill', ref = 'main') {
  // 先试 git
  try {
    return downloadViaGit(repo, ref);
  } catch (gitErr) {
    // git 失败，试 HTTPS
    try {
      return await downloadViaHttps(repo, ref);
    } catch (httpsErr) {
      throw new Error(
        `下载失败。\n` +
        `  git clone 错误: ${gitErr.message}\n` +
        `  HTTPS 下载错误: ${httpsErr.message}\n` +
        `请检查网络连接，或手动 clone 仓库后用 --source 指定本地路径。`
      );
    }
  }
}

// ---------------------------------------------------------------------------
// 从本地路径加载（用户已 clone 的情况）
// ---------------------------------------------------------------------------

export function downloadFromLocal(localPath) {
  if (!existsSync(localPath)) {
    throw new Error(`本地路径不存在: ${localPath}`);
  }
  if (!existsSync(join(localPath, 'SKILL.md'))) {
    throw new Error(`路径不包含 SKILL.md，可能不是有效的 cut.skill 仓库: ${localPath}`);
  }
  return localPath;
}
