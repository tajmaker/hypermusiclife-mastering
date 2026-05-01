import { Hero } from "../../widgets/Hero/Hero";
import { AudioScene } from "../../widgets/AudioScene/AudioScene";
import { MixerPanel } from "../../widgets/MixerPanel/MixerPanel";
import { UploadPanel } from "../../widgets/UploadPanel/UploadPanel";
import { Workflow } from "../../widgets/Workflow/Workflow";
import { useMasteringSession } from "./model/useMasteringSession";

export function MasteringPage() {
  const {state, actions} = useMasteringSession();

  return (
    <main className="page">
      <Hero status={state.track?.status || "waiting"} />
      <Workflow activeStage={state.activeStage} />
      <section className="workspace">
        <UploadPanel
          busy={state.busy}
          canPreview={state.canPreview}
          fileName={state.fileName}
          message={state.message}
          playing={state.playing}
          progress={state.progress}
          track={state.track}
          uploadDisabled={state.uploadDisabled}
          onStartOver={actions.startOver}
          onUpload={actions.upload}
          onResetControls={actions.resetControls}
        />
        <AudioScene
          controls={state.controls}
          fileName={state.fileName}
          mixerReady={state.mixerReady}
          mixMode={state.mixMode}
          playbackRevision={state.playbackRevision}
          playbackSource={state.playbackSource}
          playing={state.playing}
          readPlaybackSnapshot={state.readPlaybackSnapshot}
          stemState={state.stemState}
          track={state.track}
          onPlaybackSourceChange={actions.changePlaybackSource}
          onResetPlayback={actions.resetPlayback}
          onSeek={actions.seekPlayback}
          onTogglePlayback={actions.togglePlayback}
        />
        <MixerPanel
          busy={state.busy}
          canRender={state.canRender}
          controls={state.controls}
          downloadUrl={state.track?.urls.download || null}
          mixMode={state.mixMode}
          stemState={state.stemState}
          onChange={actions.changeControls}
          onMixModeChange={actions.changeMixMode}
          onRender={actions.render}
          onStemStateChange={actions.changeStemState}
        />
      </section>
    </main>
  );
}
