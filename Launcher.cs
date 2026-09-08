using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

namespace CTFLauncher
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string electronExe = Path.Combine(baseDir, "dist", "CTF-Notepad-win32-x64", "CTF-Notepad.exe");

                // 1. If full Electron distribution is available right next to this exe, launch it
                if (File.Exists(electronExe))
                {
                    ProcessStartInfo psi = new ProcessStartInfo(electronExe)
                    {
                        WorkingDirectory = Path.GetDirectoryName(electronExe),
                        UseShellExecute = true
                    };
                    Process.Start(psi);
                    return;
                }

                // 2. If index.html is right next to this exe, launch it
                string localHtml = Path.Combine(baseDir, "index.html");
                if (File.Exists(localHtml))
                {
                    LaunchAppMode(localHtml);
                    return;
                }

                // 3. Single-File Standalone Mode:
                // Extract embedded assets into %LOCALAPPDATA%\CTFNotepad
                string appDataDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CTFNotepad");
                Directory.CreateDirectory(appDataDir);

                ExtractResource("index.html", Path.Combine(appDataDir, "index.html"));
                ExtractResource("styles.css", Path.Combine(appDataDir, "styles.css"));
                ExtractResource("app.js", Path.Combine(appDataDir, "app.js"));

                string targetHtml = Path.Combine(appDataDir, "index.html");
                if (File.Exists(targetHtml))
                {
                    LaunchAppMode(targetHtml);
                }
                else
                {
                    MessageBox.Show("CTF 메모장 실행 자원을 추출할 수 없습니다.", "실행 오류", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("CTF 메모장 실행 중 오류 발생: " + ex.Message, "오류", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        static void LaunchAppMode(string htmlFilePath)
        {
            string absPath = Path.GetFullPath(htmlFilePath).Replace('\\', '/');
            string url = "file:///" + absPath;

            // Launch in dedicated standalone App Window mode (no browser URL bar)
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo("msedge.exe", "--app=\"" + url + "\" --window-size=1280,860")
                {
                    UseShellExecute = true
                };
                Process.Start(psi);
            }
            catch
            {
                Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
            }
        }

        static void ExtractResource(string resourceName, string outputPath)
        {
            Assembly asm = Assembly.GetExecutingAssembly();
            foreach (string name in asm.GetManifestResourceNames())
            {
                if (name.EndsWith(resourceName, StringComparison.OrdinalIgnoreCase))
                {
                    using (Stream stream = asm.GetManifestResourceStream(name))
                    {
                        if (stream != null)
                        {
                            using (FileStream fs = new FileStream(outputPath, FileMode.Create, FileAccess.Write))
                            {
                                stream.CopyTo(fs);
                            }
                        }
                    }
                    return;
                }
            }
        }
    }
}
