using System;
using System.IO;
using System.Collections.Generic;
using System.Globalization;
using Type = System.Type;
using NXOpen;
using NXOpen.Features;
using NXOpen.GeometricUtilities;
using NXOpen.UF;
using NXOpen.Utilities;

public static class Ug11Journal {
 static Part P;
 static Session S;
 static string evidence, stage="entry";
 static Dictionary<string,Expression> E=new Dictionary<string,Expression>();
 static Dictionary<string,Feature> F=new Dictionary<string,Feature>();
 static List<Ug11SketchBinding.DrivenCurveResult> driven=new List<Ug11SketchBinding.DrivenCurveResult>();
 static List<Ug11SketchBinding.DrivenSplineResult> splines=new List<Ug11SketchBinding.DrivenSplineResult>();
 static List<double[]> splineKnots=new List<double[]>();
 static List<Ug11SketchBinding.RearSlotSketch> slots=new List<Ug11SketchBinding.RearSlotSketch>();
 static void Log(string k,string v) { File.AppendAllText(evidence,k+"\t"+v+"\n"); }
 static string SafeMessage(string message) {if(String.IsNullOrEmpty(message)) return "[empty]"; if(System.Text.RegularExpressions.Regex.IsMatch(message,@"(?i)licen[cs]e|password|passwd|secret|token|credential|splm|flex|https?://|\\|/|@|[A-Z]:")) return "[redacted]"; return message.Replace("\r"," ").Replace("\n"," ").Replace("\t"," ").Substring(0,Math.Min(message.Length,300));}
 static string ShortStack(Exception ex) {var trace=new System.Diagnostics.StackTrace(ex,false); var frames=trace.GetFrames(); if(frames==null) return "none"; var result=new List<string>(); foreach(var frame in frames) {var method=frame.GetMethod(); if(method!=null && method.DeclaringType!=null) result.Add(method.DeclaringType.Name+"."+method.Name); if(result.Count==5) break;} return String.Join(",",result.ToArray());}
 static void Need(bool b,string s) {if(!b) throw new InvalidOperationException(s);}
 static void Begin(string id) {stage=id;Log("checkpoint",id+" begin");}
 static void End(string id) {Log("checkpoint",id+" complete");}
 static void UpdateModel() {var mark=S.SetUndoMark(Session.MarkVisibility.Invisible,"UG11 update"); int n=S.UpdateManager.DoUpdate(mark); Need(n==0,"model update failed");}
 static void VerifyProfiles() {foreach(var c in driven) Ug11SketchBinding.VerifyDrivenCurve(c,1e-7); for(int i=0;i<splines.Count;i++) Ug11SketchBinding.VerifyDrivenSpline(splines[i],splineKnots[i],1e-7); foreach(var slot in slots) Ug11SketchBinding.VerifyRearSlot(slot,1e-7);}
 static void VerifyNewProfiles(int c,int s,int k) {for(int i=c;i<driven.Count;i++) Ug11SketchBinding.VerifyDrivenCurve(driven[i],1e-7); for(int i=s;i<splines.Count;i++) Ug11SketchBinding.VerifyDrivenSpline(splines[i],splineKnots[i],1e-7); for(int i=k;i<slots.Count;i++) Ug11SketchBinding.VerifyRearSlot(slots[i],1e-7);}
 static void Register(string id,Feature f) {Need(f!=null && f is BodyFeature,"missing body feature"); f.SetUserAttribute("UG11_NODE",0,id,Update.Option.Now); F.Add(id,f); Log("feature",id+" "+f.JournalIdentifier);}
 static Body Live(string id) {var active=new List<Tag>(); foreach(Body b in P.Bodies.ToArray()) if(b.IsSolidBody) active.Add(b.Tag); Body found=null; int count=0; foreach(Body b in ((BodyFeature)F[id]).GetBodies()) if(active.Contains(b.Tag)) {found=b;count++;} Need(count==1,"expected one active solid for "+id); return found;}
 static void Snapshot() {int count=0; foreach(Body b in P.Bodies.ToArray()) if(b.IsSolidBody) count++; Need(count==1,"expected exactly one solid"); foreach(var item in E) Need(!item.Value.IsInterpartExpression && !Double.IsNaN(item.Value.Value) && !Double.IsInfinity(item.Value.Value),"invalid expression "+item.Key);}
 static Body FinalSolid() {Body result=null; int count=0; foreach(Body b in P.Bodies.ToArray()) if(b.IsSolidBody) {count++; result=b;} Need(count==1,"expected one final solid"); return result;}
 static void CheckStock(double diameter) {
  var read=Ug11Revolve.Readback(P,F["stock_revolve"]); var axis=(double[])read["axis_direction"]; var point=(double[])read["axis_point_mm"];
  Need(Math.Abs(axis[0])<1e-9 && Math.Abs(axis[1]-1)<1e-9 && Math.Abs(axis[2])<1e-9 && Math.Abs(point[0])+Math.Abs(point[1])+Math.Abs(point[2])<1e-9 && Math.Abs((double)read["start_degrees"])<1e-9 && Math.Abs((double)read["end_degrees"]-360)<1e-9,"stock revolve axis or angles differ");
  var inputs=(List<Tag>)read["section_input_tags"]; bool linked=false; foreach(var curve in driven) foreach(var p in curve.Points) if(p.Coordinates[0].Name=="v3_stock_R6" && inputs.Contains(curve.Curve.Tag) && Math.Abs(p.Point.Coordinates.X-diameter/2)<1e-7) linked=true;
  Need(linked,"stock revolve section is not linked to edited radius");
  bool cylinder=false; foreach(Face face in ((BodyFeature)F["stock_revolve"]).GetBodies()[0].GetFaces()) {int type,normal; double radius,data; double[] origin=new double[3],direction=new double[3],box=new double[6]; UFSession.GetUFSession().Modl.AskFaceData(face.Tag,out type,origin,direction,box,out radius,out data,out normal); if(type==16 && Math.Abs(radius-diameter/2)<1e-6 && Math.Abs(Math.Abs(direction[1])-1)<1e-7) cylinder=true;} Need(cylinder,"stock cylinder radius did not update");
 }
 static void TestDriver(string name,double low,double high) {
  string id="edit."+name; Begin(id); Expression e=E[name]; string original=e.RightHandSide; double before=e.Value;
  Need(low<high && before>=low-1e-10 && before<=high+1e-10,"driver outside tested ideal window");
  double test=Math.Abs(high-before)>=Math.Abs(before-low)?high:low; Need(Math.Abs(test-before)>1e-10,"driver test did not change");
  P.Expressions.EditWithUnits(e,e.Units,test.ToString("R",CultureInfo.InvariantCulture)); UpdateModel();
  Need(Math.Abs(e.Value-test)<1e-8,"driver value did not update"); VerifyProfiles();
  if(name=="v3_slot_width") {var limits=UG11ExtrudeSolids.ReadLimits(P,F["rear_slot_tool"]); Need(Math.Abs((double)limits["start_value"]+test/2)<1e-8 && Math.Abs((double)limits["end_value"]-test/2)<1e-8,"slot width did not drive finite extrusion");}
  if(name=="v3_c5_shaft_outer_diameter_mm") {Need(Math.Abs(E["v3_stock_R6"].Value-test/2)<1e-8 && E["v3_stock_R6"].GetUsingFeatures().Length>0,"shaft edit did not reach stock profile"); CheckStock(test);}
  P.Expressions.EditWithUnits(e,e.Units,original); UpdateModel(); Need(Math.Abs(e.Value-before)<1e-8,"driver restoration failed"); VerifyProfiles(); if(name=="v3_c5_shaft_outer_diameter_mm") CheckStock(before); Log("edit",name+" value="+test.ToString("R",CultureInfo.InvariantCulture)+" restored="+before.ToString("R",CultureInfo.InvariantCulture)); End(id);
 }
 static int SplineIndex(string id) {int found=-1; for(int i=0;i<splines.Count;i++) if(splines[i].Curve.HasUserAttribute("UG11_EDGE",NXObject.AttributeType.String,0) && splines[i].Curve.GetStringUserAttribute("UG11_EDGE",0)==id) {Need(found<0,"duplicate spline identity"); found=i;} Need(found>=0,"missing spline "+id); return found;}
 static void CheckC5Sections(int straight,int rolled) {Ug11SketchBinding.VerifyExtrudeContainsCurve(P,F["member_00_straight_tool"],splines[straight].Curve); var read=Ug11Revolve.Readback(P,F["member_00_roll_tool"]); Need(((List<Tag>)read["section_input_tags"]).Contains(splines[rolled].Curve.Tag),"roll section missing edited spline");}
 static void TestC5(double low,double high) {
  string name="v3_c5_F0002_P2_t_mm", id="edit."+name; Begin(id); Expression e=E[name]; string original=e.RightHandSide; double before=e.GetValueUsingUnits(Expression.UnitsOption.Expression); Need(low<high && before>=low && before<=high,"C5 driver outside ideal window"); double test=Math.Abs(high-before)>=Math.Abs(before-low)?high:low;
  int a=SplineIndex("member_00_straight_tool/edge/4"), b=SplineIndex("member_00_roll_tool/edge/4"); CheckC5Sections(a,b);
  Point3d[] pa=Ug11SketchBinding.CaptureSplinePoles(splines[a],splineKnots[a],1e-8), pb=Ug11SketchBinding.CaptureSplinePoles(splines[b],splineKnots[b],1e-8);
  P.Expressions.EditWithUnits(e,e.Units,test.ToString("R",CultureInfo.InvariantCulture)); UpdateModel(); Need(Math.Abs(e.GetValueUsingUnits(Expression.UnitsOption.Expression)-test)<1e-9,"C5 source edit mismatch");
  double da=Ug11SketchBinding.VerifySplineEdited(splines[a],splineKnots[a],pa,1e-8,1e-7), db=Ug11SketchBinding.VerifySplineEdited(splines[b],splineKnots[b],pb,1e-8,1e-7); CheckC5Sections(a,b);
  P.Expressions.EditWithUnits(e,e.Units,original); UpdateModel(); Need(Math.Abs(e.GetValueUsingUnits(Expression.UnitsOption.Expression)-before)<1e-9,"C5 source restoration mismatch"); Point3d[] ra=Ug11SketchBinding.CaptureSplinePoles(splines[a],splineKnots[a],1e-8), rb=Ug11SketchBinding.CaptureSplinePoles(splines[b],splineKnots[b],1e-8); Need(ra.Length==pa.Length && rb.Length==pb.Length,"C5 pole count changed"); for(int i=0;i<ra.Length;i++) Need(Math.Abs(ra[i].X-pa[i].X)+Math.Abs(ra[i].Y-pa[i].Y)+Math.Abs(ra[i].Z-pa[i].Z)<1e-7,"straight spline restoration mismatch"); for(int i=0;i<rb.Length;i++) Need(Math.Abs(rb[i].X-pb[i].X)+Math.Abs(rb[i].Y-pb[i].Y)+Math.Abs(rb[i].Z-pb[i].Z)<1e-7,"rolled spline restoration mismatch"); CheckC5Sections(a,b); Log("edit",name+" straight_max_mm="+da.ToString("R",CultureInfo.InvariantCulture)+" roll_max_mm="+db.ToString("R",CultureInfo.InvariantCulture)); End(id);
 }
 static SortedSet<string> EdgeIds() {var ids=new SortedSet<string>(); foreach(Curve c in P.Curves.ToArray()) if(c.HasUserAttribute("UG11_EDGE",NXObject.AttributeType.String,0)) Need(ids.Add(c.GetStringUserAttribute("UG11_EDGE",0)),"duplicate edge identity"); return ids;}
 static void CheckReopen(SortedSet<string> expectedFeatures,SortedSet<string> expectedEdges,Dictionary<string,string> rhs,Dictionary<string,double> values,int faces,int edges) {
  int bodyCount=0; foreach(Body b in P.Bodies.ToArray()) if(b.IsSolidBody) bodyCount++; Need(bodyCount==1,"reopen solid mismatch");
  var names=new SortedSet<string>(); int count=0; foreach(Feature f in P.Features.GetFeatures()) if(f.HasUserAttribute("UG11_NODE",NXObject.AttributeType.String,0)) {count++; names.Add(f.GetStringUserAttribute("UG11_NODE",0));}
  Need(count==expectedFeatures.Count && expectedFeatures.SetEquals(names),"reopen feature identity mismatch");
  Need(expectedEdges.SetEquals(EdgeIds()),"reopen profile identity mismatch");
  Need(FinalSolid().GetFaces().Length==faces && FinalSolid().GetEdges().Length==edges,"reopen topology count mismatch"); Log("reopen_topology","faces="+faces+" edges="+edges);
  var byName=new Dictionary<string,Expression>(); foreach(Expression expression in P.Expressions.ToArray()) byName.Add(expression.Name,expression);
  foreach(var name in rhs.Keys) {Need(byName.ContainsKey(name),"reopen expression missing "+name); Expression e=byName[name]; Need(!e.IsInterpartExpression && e.RightHandSide==rhs[name] && Math.Abs(e.Value-values[name])<1e-8,"reopen expression mismatch "+name);}
  Extrude tail=null; foreach(Feature f in P.Features.GetFeatures()) if(f.HasUserAttribute("UG11_NODE",NXObject.AttributeType.String,0) && f.GetStringUserAttribute("UG11_NODE",0)=="rear_slot_tool") {Need(tail==null && f is Extrude,"ambiguous rear-slot extrusion"); tail=(Extrude)f;} Need(tail!=null,"rear-slot extrusion missing");
  var slot=Ug11SketchBinding.ReopenRearSlot(P); Ug11SketchBinding.VerifyRearSlot(slot,1e-7); Ug11SketchBinding.VerifyRearSlotConsumer(P,tail,slot);
 }
 @METHODS@
 public static void Main(string[] args) {
  evidence=Environment.GetEnvironmentVariable("UG11_EVIDENCE"); string path=Environment.GetEnvironmentVariable("UG11_MODEL");
  if(String.IsNullOrEmpty(evidence)||String.IsNullOrEmpty(path)||!File.Exists(evidence)||File.Exists(path)||String.Equals(Path.GetFullPath(evidence),Path.GetFullPath(path),StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("invalid output paths");
  try {
   S=Session.GetSession(); UFSession uf=UFSession.GetUFSession(); string release; uf.UF.GetRelease(out release); var version=System.Diagnostics.FileVersionInfo.GetVersionInfo(typeof(Session).Assembly.Location); string assembly=typeof(Session).Assembly.GetName().Version.ToString(); string lang=Environment.GetEnvironmentVariable("UGII_LANG");
   Log("native_release",release); Log("runtime","assembly="+assembly+" file="+version.FileVersion+" product="+version.ProductVersion+" language="+lang);
   Need(release=="NX V11.0" && assembly=="11.0.0.33" && version.FileVersion=="11.0.0.33" && version.ProductVersion=="11.0.0.33" && lang=="simpl_chinese","unsupported runtime"); Need(S.Parts.Work==null && S.Parts.Display==null,"session is not blank");
   P=S.Parts.NewDisplay(path,Part.Units.Millimeters); double dist=0.00025, angle=0.01; uf.Modl.SetDistanceTolerance(ref dist); uf.Modl.SetAngleTolerance(ref angle); double actualDist,actualAngle; uf.Modl.AskDistanceTolerance(out actualDist); uf.Modl.AskAngleTolerance(out actualAngle); Need(Math.Abs(actualDist-dist)<1e-12 && Math.Abs(actualAngle-angle)<1e-12,"model tolerance readback mismatch");
   @CALLS@
   @EDITS@
   UpdateModel(); VerifyProfiles(); Snapshot(); Body finalBody=FinalSolid(); int faces=finalBody.GetFaces().Length, edges=finalBody.GetEdges().Length; Need(faces>0 && edges>0,"final topology empty"); Log("topology","faces="+faces+" edges="+edges); var expectedFeatures=new SortedSet<string>(F.Keys); var expectedEdges=EdgeIds(); Need(expectedEdges.Count>0,"profile identities missing"); var expectedRhs=new Dictionary<string,string>(); var expectedValues=new Dictionary<string,double>(); foreach(var item in E) {expectedRhs.Add(item.Key,item.Value.RightHandSide); expectedValues.Add(item.Key,item.Value.Value);}
   Begin("save"); using(PartSaveStatus status=P.Save(BasePart.SaveComponents.True,BasePart.CloseAfterSave.False)) Need(status.NumberUnsavedParts==0 && status.NumberUnsavedObjects==0 && !uf.Part.IsModified(P.Tag),"save incomplete"); End("save");
   Begin("close"); P.Close(BasePart.CloseWholeTree.False,BasePart.CloseModified.CloseModified,null); Need(S.Parts.Work==null && S.Parts.Display==null,"part still open"); byte[] saved=Ug11ReadOnlyClose.Capture(path); End("close");
   Begin("reopen"); PartLoadStatus load; P=S.Parts.OpenDisplay(path,out load); using(load) Need(load.NumberUnloadedParts==0,"unloaded part"); bool beforeRead=uf.Part.IsModified(P.Tag); Log("dirty_before_readback",beforeRead.ToString()); Need(!beforeRead,"reopened part already modified before readback"); CheckReopen(expectedFeatures,expectedEdges,expectedRhs,expectedValues,faces,edges); bool afterRead=uf.Part.IsModified(P.Tag); Log("dirty_after_readback",afterRead.ToString()); End("reopen");
   Begin("final_close"); Ug11ReadOnlyClose.Close(P,S,path,saved); Log("closed_without_save","byte_for_byte_unchanged"); End("final_close"); Log("result","PASS");
  } catch(Exception ex) {Log("failure","stage="+stage+" type="+ex.GetType().FullName+" nx_error="+(ex is NXException?((NXException)ex).ErrorCode.ToString(CultureInfo.InvariantCulture):"none")+" message="+SafeMessage(ex.Message)+" stack="+ShortStack(ex)+" state=UNKNOWN; do not replay");}
 }
 public static int GetUnloadOption(string arg) {return (int)Session.LibraryUnloadOption.Immediately;}
}

