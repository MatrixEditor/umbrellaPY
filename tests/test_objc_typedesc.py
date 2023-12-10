from umbrella.objc import decoder


def assert_desc(original, expected) -> None:
    desc = decoder.objc_typedesc(original)
    assert decoder.objc_decode(desc) == expected


def assert_sig(selector, original, expected) -> None:
    assert decoder.objc_signature(selector, original) == expected


def test_property_typedesc():
    assert_desc('T@"NSMutableArray",&,D,N', "@dynamic @property (retain, nonatomic) NSMutableArray")
    assert_desc('TI,R,D,N', "@dynamic @property (readonly, nonatomic) unsigned int")
    assert_desc('T@"NSString",C,D,N', "@dynamic @property (copy, nonatomic) NSString")
    assert_desc('Tc,D,N', "@dynamic @property (nonatomic) char")
    assert_desc('T@"CYCProcessingService",&,N,V_processingService', "@property (retain, nonatomic) CYCProcessingService processingService")
    assert_desc('T@"GOOPanelViewController",&,N,V_galleryPanelVC', "@property (retain, nonatomic) GOOPanelViewController galleryPanelVC")
    assert_desc('T@"CYCGalleryViewController",&,N,V_galleryVC', "@property (retain, nonatomic) CYCGalleryViewController galleryVC")
    assert_desc('T@"NSString",&,N,V_pendingShareKey', "@property (retain, nonatomic) NSString pendingShareKey")
    assert_desc('T@"UIWindow",&,N,V_window', "@property (retain, nonatomic) UIWindow window")
    assert_desc('TI,R', "@property (readonly) unsigned int")
    assert_desc('T#,R', "@property (readonly) Class")
    assert_desc('T@"NSString",R,C', "@property (readonly, copy) NSString")
    assert_desc('T@"NSString",R,C', "@property (readonly, copy) NSString")


def test_method_typedesc():
    assert_sig("foo:", "v12@0:4^{Bar=}8", "(void)foo:(struct Bar *)")
    assert_sig("initWithFrame:", "@24@0:4{CGRect={CGPoint=ff}{CGSize=ff}}8", "(id)initWithFrame:(struct CGRect)")
    assert_sig("setText:showImage:dismissAction:", "v20@0:4@8c12@?16", "(void)setText:(id) showImage:(char) dismissAction:(id)")
    assert_sig("toggleRecordSound", "v8@0:4", "(void)toggleRecordSound")
    assert_sig("recordSoundEnabled", "c8@0:4", "(char)recordSoundEnabled")
    assert_sig("videoSession:didStopRunningWithError:", "v16@0:4@8@12", "(void)videoSession:(id) didStopRunningWithError:(id)")
    assert_sig("videoSession:permission:granted:", "v20@0:4@8I12c16", "(void)videoSession:(id) permission:(unsigned int) granted:(char)")
    assert_sig("sampleBufferListener:display:", "v16@0:4@8^{__CVBuffer=}12", "(void)sampleBufferListener:(id) display:(struct __CVBuffer *)")
