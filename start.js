// 1. read proxies from file
const fs = require('fs')
const path = require('path')
require('console-stamp')(console, {
  format: ':date(yyyy/mm/dd HH:MM:ss.l)'
})

let proxies = []

try {
  proxies = fs.readFileSync(path.resolve(__dirname, 'proxies.txt'), 'utf-8').split('\n').filter(Boolean)
} catch (error) {
  console.log('-> No proxies.txt found, or error reading file, will start app without proxy...')
}

// 2. start pm2 with PROXY env
const { execSync } = require('child_process')
const USER = process.env.APP_USER || ''
const PASSWORD = process.env.APP_PASS || ''

if (!USER || !PASSWORD) {
  console.error("Please set APP_USER and APP_PASS env variables")
  process.exit()
}

if (proxies.length === 0) {
  console.error("No proxies found in proxies.txt, will start app without proxy...")
  execSync(`APP_USER='${USER}' APP_PASS='${PASSWORD}' pm2 start app.js --name gradient-bot-no-proxy -l gradient-bot-no-proxy.log`)
  console.log('->  √ Started gradient-bot-no-proxy')
} else {
  console.log(`-> Found ${proxies.length} proxies in proxies.txt`)
  let index = 0
  for (const proxy of proxies) {
    const name = `gradient-${index++}`
    execSync(`PROXY=${proxy} APP_USER='${USER}' APP_PASS='${PASSWORD}' pm2 start app.js --name ${name} -l ${name}.log`)
    console.log(`-> Started ${name} with proxy ${proxy}`)
  }

  // 3. save proxies to file
  console.log('-> √ All proxies started!')
}

// 4. pm2 status
execSync('pm2 status')
