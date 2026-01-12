import { useState, useEffect } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { HomeTab } from "./tabs/HomeTab";
import { ProxyTab } from "./tabs/ProxyTab";
import { ProjectTab } from "./tabs/ProjectTab";
import { ResenderTab } from "./tabs/ResenderTab";
import { AgentTab } from "./tabs/AgentTab";
import { useResender } from "@/contexts/ResenderContext";
import { StatusIndicators } from "./StatusIndicators";
import { Home, Repeat, Globe, Folder, Bot } from "lucide-react";

export const AppTabs = () => {
  const { tabs, setNavigateCallback } = useResender();
  const [activeMainTab, setActiveMainTab] = useState("home");

  useEffect(() => {
    setNavigateCallback(() => {
      setActiveMainTab("resender");
    });
  }, [setNavigateCallback]);
  
  return (
    <Tabs value={activeMainTab} onValueChange={setActiveMainTab} className="flex-1 flex flex-col min-h-0">
      <div className="border-b bg-card px-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="font-logo text-2xl font-bold text-primary tracking-tight">
              moxy
            </span>
          </div>
          <TabsList className="h-12 gap-1 bg-transparent p-0">
            <TabsTrigger 
              value="home" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors"
            >
              <Home className="h-4 w-4" />
              Home
            </TabsTrigger>
            <TabsTrigger 
              value="resender" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors"
            >
              <Repeat className="h-4 w-4" />
              Resender
              {tabs.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-primary/20 text-primary">
                  {tabs.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger 
              value="proxy" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors"
            >
              <Globe className="h-4 w-4" />
              Proxy
            </TabsTrigger>
            <TabsTrigger 
              value="project" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors"
            >
              <Folder className="h-4 w-4" />
              Project
            </TabsTrigger>
            <TabsTrigger 
              value="agent" 
              className="data-[state=active]:bg-muted data-[state=active]:shadow-none gap-2 px-4 hover:bg-success/10 transition-colors"
            >
              <Bot className="h-4 w-4" />
              Agent
            </TabsTrigger>
          </TabsList>
        </div>
        
        {/* Status Indicators */}
        <StatusIndicators onProxyClick={() => setActiveMainTab("proxy")} />
      </div>
      
      <TabsContent value="home" className="flex-1 mt-0 min-h-0">
        <HomeTab />
      </TabsContent>
      <TabsContent value="resender" className="flex-1 mt-0 min-h-0">
        <ResenderTab />
      </TabsContent>
      <TabsContent value="proxy" className="flex-1 mt-0 min-h-0">
        <ProxyTab />
      </TabsContent>
      <TabsContent value="project" className="flex-1 mt-0 min-h-0">
        <ProjectTab />
      </TabsContent>
      <TabsContent value="agent" className="flex-1 mt-0 min-h-0">
        <AgentTab />
      </TabsContent>
    </Tabs>
  );
};
