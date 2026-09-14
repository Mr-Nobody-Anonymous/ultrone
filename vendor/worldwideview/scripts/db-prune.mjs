/**
 * @file db-prune.mjs
 * @description Garbage collects orphaned Docker volumes from deleted git worktrees.
 * Resolves the issue where manually deleting a worktree folder (rm -rf) leaves 
 * behind persistent database and data volumes.
 */

import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

console.log('🧹 Starting Garbage Collection for orphaned WorldWideView Docker volumes...');

try {
  // Get all docker volumes
  const volumesOutput = execSync('docker volume ls --format "{{.Name}}"').toString();
  const volumes = volumesOutput.split('\n').map(v => v.trim()).filter(Boolean);

  // Identify WorldWideView volumes
  const wwvVolumes = volumes.filter(v => 
    (v.startsWith('worldwideview') && v.endsWith('_postgres-data')) || 
    (v.startsWith('worldwideview') && v.endsWith('_wwv-data'))
  );

  if (wwvVolumes.length === 0) {
    console.log('✅ No WorldWideView volumes found.');
    process.exit(0);
  }

  // Get active worktree folders in the parent directory
  const parentDir = path.resolve(process.cwd(), '..');
  const folders = fs.readdirSync(parentDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory() && dirent.name.startsWith('worldwideview'))
    .map(dirent => dirent.name);

  // Compute their expected Docker project names (lowercase, alphanumeric only)
  // Docker Compose defaults to this sanitization for project names based on directories
  const activeProjectNames = new Set(
    folders.map(folder => folder.replace(/[^a-zA-Z0-9]/g, '').toLowerCase())
  );

  let orphanedCount = 0;

  for (const volume of wwvVolumes) {
    let projectName = '';
    if (volume.endsWith('_postgres-data')) {
      projectName = volume.slice(0, -'_postgres-data'.length);
    } else if (volume.endsWith('_wwv-data')) {
      projectName = volume.slice(0, -'_wwv-data'.length);
    }

    if (!activeProjectNames.has(projectName)) {
      console.log(`🗑️  Deleting orphaned volume: ${volume}`);
      try {
        execSync(`docker volume rm ${volume}`, { stdio: 'inherit' });
        orphanedCount++;
      } catch (rmError) {
        console.warn(`⚠️  Could not remove volume ${volume}. It may still be in use.`);
      }
    }
  }

  if (orphanedCount === 0) {
    console.log('✅ All existing volumes belong to active worktrees. Nothing to prune.');
  } else {
    console.log(`✅ Successfully pruned ${orphanedCount} orphaned volume(s).`);
  }

} catch (error) {
  console.error('❌ Failed to prune volumes:', error.message);
  process.exit(1);
}
