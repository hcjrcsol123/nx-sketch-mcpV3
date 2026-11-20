using System;
using System.IO;
using NXOpen;

// Only close a just-saved independent part after the caller has performed
// explicitly read-only verification. No save, recovery or retry is performed.
public static class Ug11ReadOnlyClose {
 public static byte[] Capture(string path) {if(String.IsNullOrEmpty(path) || !File.Exists(path)) throw new InvalidOperationException("saved copy missing"); return File.ReadAllBytes(path);}
 public static void VerifyBytes(string path,byte[] expected) {byte[] actual=Capture(path); if(expected==null || actual.Length!=expected.Length) throw new InvalidOperationException("saved copy bytes changed"); for(int i=0;i<actual.Length;i++) if(actual[i]!=expected[i]) throw new InvalidOperationException("saved copy bytes changed");}
 public static void Close(Part part,Session session,string path,byte[] expected) {
  if(part==null || session==null || session.Parts.Work==null || session.Parts.Display==null || session.Parts.Work.Tag!=part.Tag || session.Parts.Display.Tag!=part.Tag) throw new InvalidOperationException("unexpected current part");
  VerifyBytes(path,expected);
  part.Close(BasePart.CloseWholeTree.False,BasePart.CloseModified.CloseModified,null);
  if(session.Parts.Work!=null || session.Parts.Display!=null) throw new InvalidOperationException("part remained open");
  VerifyBytes(path,expected);
 }
}
