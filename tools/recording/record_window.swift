// Records only the selected Kyna application window, without microphone or system audio.
import Foundation
import AppKit
import ScreenCaptureKit
import AVFoundation

final class Recorder: NSObject, SCStreamOutput, @unchecked Sendable {
    let writer: AVAssetWriter
    let input: AVAssetWriterInput
    var started = false
    init(url: URL, width: Int, height: Int) throws {
        writer = try AVAssetWriter(outputURL: url, fileType: .mp4)
        input = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: width, AVVideoHeightKey: height])
        input.expectsMediaDataInRealTime = true
        super.init()
        writer.add(input)
    }
    func stream(_ stream: SCStream, didOutputSampleBuffer sample: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, sample.isValid else { return }
        guard let attachments = CMSampleBufferGetSampleAttachmentsArray(sample, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let status = attachments.first?[.status] as? Int, status == SCFrameStatus.complete.rawValue else { return }
        if !started {
            guard writer.startWriting() else { return }
            writer.startSession(atSourceTime: sample.presentationTimeStamp)
            started = true
        }
        if input.isReadyForMoreMediaData { input.append(sample) }
    }
}
@main struct Main {
    static func main() async throws {
        _ = NSApplication.shared
        let arguments = CommandLine.arguments
        guard arguments.count == 4, let seconds = Double(arguments[3]), seconds > 0, seconds <= 120 else {
            throw NSError(domain: "KynaRecording", code: 1, userInfo: [NSLocalizedDescriptionKey:"Usage: record-window <exact window title> <output.mp4> <seconds 1..120>"])
        }
        let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
        let matches = content.windows.filter { $0.title == arguments[1] }
        guard matches.count == 1 else { throw NSError(domain:"KynaRecording", code:2, userInfo:[NSLocalizedDescriptionKey:"Expected exactly one matching application window"])}
        let window = matches[0]
        let configuration = SCStreamConfiguration()
        configuration.width = Int(window.frame.width) / 2 * 2
        configuration.height = Int(window.frame.height) / 2 * 2
        configuration.minimumFrameInterval = CMTime(value: 1, timescale: 30)
        configuration.showsCursor = false
        configuration.capturesAudio = false
        let recorder = try Recorder(url: URL(fileURLWithPath: arguments[2]), width: configuration.width, height: configuration.height)
        let queue = DispatchQueue(label: "org.kyna.recording")
        let stream = SCStream(filter: SCContentFilter(desktopIndependentWindow: window), configuration: configuration, delegate: nil)
        try stream.addStreamOutput(recorder, type: .screen, sampleHandlerQueue: queue)
        try await stream.startCapture()
        print("RECORDING_STARTED window=\(arguments[1])")
        try await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
        try await stream.stopCapture()
        queue.sync { recorder.input.markAsFinished() }
        await recorder.writer.finishWriting()
        guard recorder.writer.status == .completed else { throw recorder.writer.error ?? NSError(domain:"KynaRecording", code:3)}
        print("RECORDING_COMPLETE")
    }
}
